#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, Any, Optional, Tuple
import re
import uuid

from ..models.schemas import QnAResponse, Suggestion, UserInfoRequest, ServiceResponse
from ..models.platform_models import PlatformContext
from ..core.conversation_memory import ConversationMemory
from ..services.email_service import EmailService
from ..llm.open_client import OpenAIClient
from ..agents.service_agent import ServiceAgent


class BookingAgent:
    """Conversational booking agent that incrementally collects user info and sends emails when confirmed."""

    def __init__(self, memory: ConversationMemory, email_service: Optional[EmailService] = None, llm_client: Optional[OpenAIClient] = None, service_agent: Optional[ServiceAgent] = None):
        self.memory = memory
        self.email_service = email_service
        self.llm_client = llm_client or OpenAIClient()
        self.service_agent = service_agent

    async def handle(self, conversation_id: str, message: str, platform_context: PlatformContext) -> QnAResponse:
        """Process a booking-related user message.

        Strategy:
        - Merge newly extracted info into booking state in memory
        - Ask for the next missing field(s)
        - If user confirmed and required fields present, send emails and finalize
        """
        state = self._get_booking_state(conversation_id)

        # Bootstrap state
        if not state:
            state = {
                "status": "collecting",  # collecting | ready | submitted
                "name": None,
                "email": None,
                "phone": None,
                "restaurant": None,
                "party_size": None,
                "time": None,
                "special_request": None,
                "confirmed": False,
            }

            # Use last mentioned place from memory if available
            entities = self.memory.get_entities(conversation_id)
            last_place = entities.get("current_place") or entities.get("last_mentioned_place")
            if last_place:
                state["restaurant"] = last_place

        # If waiting for a restaurant choice, try to select from recommendations
        if state.get("awaiting_restaurant_selection") and state.get("recommendations"):
            selection = self._extract_restaurant_selection(message, state["recommendations"], platform_context.language.value)
            if selection:
                state["restaurant"] = selection.get("name")
                state["restaurant_id"] = selection.get("id")
                state["awaiting_restaurant_selection"] = False

        # Extract info from current user message (LLM first, fallback to heuristics)
        extracted = self._llm_extract_and_plan(state, message, platform_context.language.value)
        if not extracted:
            extracted = self._extract_booking_info(message, platform_context.language.value)
        for key, value in (extracted or {}).items():
            if value:
                state[key] = value

        # If restaurant still missing and user asks to find/suggest, switch to discovery using ServiceAgent
        if not state.get("restaurant") and self._is_discovery_message(message, platform_context.language.value):
            if self.service_agent:
                services_resp: ServiceResponse = await self.service_agent.get_services(
                    query=message,
                    platform_context=platform_context,
                    service_type="restaurant"
                )
                recs = []
                for s in (services_resp.services or [])[:5]:
                    recs.append({"id": getattr(s, "id", None), "name": getattr(s, "name", ""), "type": getattr(s, "type", "restaurant")})
                if recs:
                    state["recommendations"] = recs
                    state["awaiting_restaurant_selection"] = True
                    self._set_booking_state(conversation_id, state)
                    # Build response asking user to choose
                    if platform_context.language.value == "vi":
                        names = ", ".join([r["name"] for r in recs[:3]])
                        answer = f"Mình gợi ý vài địa điểm: {names}. Bạn có thể chọn số 1/2/3 hoặc gõ tên nhà hàng."
                        suggestions = [
                            Suggestion(label=f"Chọn 1: {recs[0]['name']}", detail=None, action="select_restaurant") if len(recs) > 0 else None,
                            Suggestion(label=f"Chọn 2: {recs[1]['name']}", detail=None, action="select_restaurant") if len(recs) > 1 else None,
                            Suggestion(label=f"Chọn 3: {recs[2]['name']}", detail=None, action="select_restaurant") if len(recs) > 2 else None,
                        ]
                        suggestions = [s for s in suggestions if s]
                    else:
                        names = ", ".join([r["name"] for r in recs[:3]])
                        answer = f"Here are some places: {names}. You can pick 1/2/3 or type the restaurant name."
                        suggestions = [
                            Suggestion(label=f"Pick 1: {recs[0]['name']}", detail=None, action="select_restaurant") if len(recs) > 0 else None,
                            Suggestion(label=f"Pick 2: {recs[1]['name']}", detail=None, action="select_restaurant") if len(recs) > 1 else None,
                            Suggestion(label=f"Pick 3: {recs[2]['name']}", detail=None, action="select_restaurant") if len(recs) > 2 else None,
                        ]
                        suggestions = [s for s in suggestions if s]
                    return QnAResponse(type="QnA", answerAI=answer, sources=services_resp.sources or [], suggestions=suggestions)

        # Detect confirmation keywords
        if self._is_confirmation(message, platform_context.language.value):
            state["confirmed"] = True

        # Determine missing fields with priority: booking details first, then contact info
        priority_missing = self._get_priority_missing_fields(state)
        # Determine missing mandatory contact fields for readiness check
        missing_required = self._get_missing_required_fields(state)

        # Ready to submit when no missing and user confirmed
        if not missing_required:
            state["status"] = "ready"

        # If ready and confirmed, send emails and finalize
        if state["status"] == "ready" and state.get("confirmed"):
            booking_reference = f"TRIPC-{uuid.uuid4().hex[:8].upper()}"

            # Build UserInfoRequest payload
            info_message = self._compose_summary_message(state, platform_context.language.value)

            user_info = UserInfoRequest(
                name=state.get("name") or "",
                email=state.get("email") or "",
                phone=state.get("phone") or "",
                message=f"{info_message} | Ref: {booking_reference}",
                service_interest=state.get("restaurant"),
                location=None,
                platform=platform_context.platform,
                device=platform_context.device,
                language=platform_context.language,
            )

            # Try sending emails if service configured
            sent_company = False
            sent_user = False
            if self.email_service and self.email_service.is_smtp_configured():
                try:
                    sent_company = await self.email_service.send_booking_inquiry(user_info)
                    sent_user = await self.email_service.send_confirmation_email(user_info)
                except Exception:
                    sent_company = False
                    sent_user = False

            # Finalize state
            state["status"] = "submitted"
            self._set_booking_state(conversation_id, state)

            # Compose final response
            if platform_context.language.value == "vi":
                answer = (
                    "Đã ghi nhận yêu cầu đặt chỗ. "
                    f"Mã tham chiếu: {booking_reference}. "
                    + ("Email đã được gửi đến bạn." if sent_user else "(Chưa gửi email xác nhận do cấu hình SMTP.)")
                )
                suggestions = [
                    Suggestion(label="Tìm thêm nhà hàng", detail="Khám phá địa điểm khác", action="show_more_services"),
                    Suggestion(label="Tư vấn thêm", detail="Hỏi đáp về địa điểm/ẩm thực", action="qna")
                ]
            else:
                answer = (
                    "Your reservation request has been recorded. "
                    f"Reference: {booking_reference}. "
                    + ("A confirmation email has been sent." if sent_user else "(Confirmation email not sent due to SMTP config.)")
                )
                suggestions = [
                    Suggestion(label="See more restaurants", detail="Explore other places", action="show_more_services"),
                    Suggestion(label="Ask more", detail="Q&A about destinations/food", action="qna")
                ]

            return QnAResponse(type="QnA", answerAI=answer, sources=[], suggestions=suggestions)

        # Not ready -> ask for next missing info (booking details first)
        self._set_booking_state(conversation_id, state)
        ask_text = self._compose_next_question(state, priority_missing, platform_context.language.value)
        suggestions = self._next_suggestions(missing_required, platform_context.language.value)

        return QnAResponse(type="QnA", answerAI=ask_text, sources=[], suggestions=suggestions)

    def _get_booking_state(self, conversation_id: str) -> Dict[str, Any]:
        entities = self.memory.get_entities(conversation_id)
        return entities.get("booking", {})

    def _set_booking_state(self, conversation_id: str, state: Dict[str, Any]) -> None:
        entities = self.memory.get_entities(conversation_id)
        entities["booking"] = state
        self.memory.set_entities(conversation_id, entities)

    def _get_missing_required_fields(self, state: Dict[str, Any]) -> Tuple[str, ...]:
        missing = []
        for field in ("name", "phone", "email"):
            if not state.get(field):
                missing.append(field)
        return tuple(missing)

    def _get_priority_missing_fields(self, state: Dict[str, Any]) -> Tuple[str, ...]:
        order = ("restaurant", "party_size", "time", "name", "phone", "email")
        missing = []
        for field in order:
            if not state.get(field):
                missing.append(field)
        return tuple(missing)

    def _is_confirmation(self, text: str, lang: str) -> bool:
        t = text.lower().strip()
        vi_words = ["chốt", "xác nhận", "đồng ý", "ok", "okie", "oke", "gửi đi", "gửi", "hoàn tất"]
        en_words = ["confirm", "ok", "okay", "send", "proceed", "done", "finish"]
        words = vi_words if lang == "vi" else en_words
        return any(w in t for w in words)

    def _extract_booking_info(self, text: str, lang: str) -> Dict[str, Optional[str]]:
        """Very lightweight extraction for name/email/phone/party size/time/restaurant/special.
        These are best-effort heuristics; robust extraction should be handled by LLM in future.
        """
        result: Dict[str, Optional[str]] = {
            "name": None,
            "email": None,
            "phone": None,
            "party_size": None,
            "time": None,
            "restaurant": None,
            "special_request": None,
        }

        # Email
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", text)
        if email_match:
            result["email"] = email_match.group(0)

        # Phone (simple VN format detection)
        phone_match = re.search(r"\+?\d{9,13}", text.replace(" ", ""))
        if phone_match:
            result["phone"] = phone_match.group(0)

        # Party size (people)
        people_match = re.search(r"(\d+)\s*(người|nguoi|pax|people)", text.lower())
        if people_match:
            result["party_size"] = people_match.group(1)

        # Time (very simple hh or hh:mm and common words like tối/chiều/tối nay)
        time_match = re.search(r"(\d{1,2}(:\d{2})?\s*(pm|am)?)", text.lower())
        if time_match:
            result["time"] = time_match.group(1)
        else:
            for w in ["tối", "trưa", "sáng", "tối nay", "chiều", "tonight", "this evening", "lunch", "dinner", "breakfast"]:
                if w in text.lower():
                    result["time"] = w
                    break

        # Restaurant name (e.g., "nhà hàng Bông" or quoted)
        rest_match = re.search(r"nhà hàng\s+([A-Za-zÀ-ỹ0-9'\-\s]+)", text, flags=re.IGNORECASE)
        if rest_match:
            result["restaurant"] = rest_match.group(1).strip().strip("'\"")
        else:
            quoted = re.search(r"['\"]([^'\"]{2,})['\"]", text)
            if quoted:
                result["restaurant"] = quoted.group(1).strip()

        # Special request
        if any(k in text.lower() for k in ["ghi chú", "note", "yêu cầu", "request"]):
            # crude: take full sentence
            result["special_request"] = text

        # Name keyword (if user types: Tên: ...)
        name_match = re.search(r"(tên|name)\s*:\s*([^,\n\r]{2,})", text, flags=re.IGNORECASE)
        if name_match:
            result["name"] = name_match.group(2).strip()

        return result

    def _llm_extract_and_plan(self, state: Dict[str, Any], message: str, lang: str) -> Optional[Dict[str, Optional[str]]]:
        """Use LLM to extract booking fields and decide next actions. Returns extracted field updates.
        If LLM not configured or fails, return None.
        """
        try:
            if not self.llm_client or not self.llm_client.is_configured():
                return None

            # Build compact state snapshot for the LLM
            snapshot = {
                "name": state.get("name"),
                "email": state.get("email"),
                "phone": state.get("phone"),
                "restaurant": state.get("restaurant"),
                "party_size": state.get("party_size"),
                "time": state.get("time"),
                "special_request": state.get("special_request"),
            }

            if lang == "vi":
                system = (
                    "Bạn là tác tử hỗ trợ ĐẶT CHỖ. Hãy phân tích tin nhắn và TRẢ VỀ JSON duy nhất với các khóa: \n"
                    "updates: {name|email|phone|restaurant|party_size|time|special_request}, giá trị là chuỗi hoặc null.\n"
                    "missing: mảng các trường quan trọng còn thiếu trong [name, email, phone].\n"
                    "is_ready: true/false nếu đủ 3 trường bắt buộc.\n"
                    "ask: câu hỏi ngắn gọn tiếp theo (nếu chưa đủ).\n"
                    "Không thêm lời giải thích khác."
                )
                user = (
                    f"Trạng thái hiện tại: {snapshot}.\n"
                    f"Tin nhắn người dùng: {message}.\n"
                    "Hãy trả JSON."
                )
            else:
                system = (
                    "You are a BOOKING assistant. Analyze the message and RETURN a single JSON with keys:\n"
                    "updates: {name|email|phone|restaurant|party_size|time|special_request} (string or null).\n"
                    "missing: array of required fields still missing among [name, email, phone].\n"
                    "is_ready: true/false if all required fields are present.\n"
                    "ask: the next concise question (if not ready).\n"
                    "No extra text."
                )
                user = (
                    f"Current state: {snapshot}.\n"
                    f"User message: {message}.\n"
                    "Return JSON."
                )

            prompt = f"System: {system}\n\nUser: {user}"
            out = self.llm_client.generate_response(prompt, max_tokens=220, temperature=0.2)
            if not out:
                return None

            # Extract JSON
            import json, re
            m = re.search(r"\{[\s\S]*\}", out)
            if not m:
                return None
            data = json.loads(m.group(0))

            # Persist suggested next ask into state so we can surface it
            if data.get("ask"):
                state["next_ask"] = data["ask"]

            # Merge updates
            updates = data.get("updates") or {}
            extracted: Dict[str, Optional[str]] = {}
            for key in ["name", "email", "phone", "restaurant", "party_size", "time", "special_request"]:
                val = updates.get(key)
                if isinstance(val, str) and val.strip():
                    extracted[key] = val.strip()

            return extracted or None
        except Exception:
            return None

    def _is_discovery_message(self, message: str, lang: str) -> bool:
        m = message.lower()
        vi_triggers = ["tìm", "gợi ý", "gần", "xung quanh", "khu vực", "cầu rồng", "bán đảo sơn trà", "biển", "near", "around"]
        en_triggers = ["find", "suggest", "near", "around", "area"]
        triggers = vi_triggers if lang == "vi" else en_triggers
        return any(t in m for t in triggers)

    def _extract_restaurant_selection(self, message: str, recommendations: list[Dict[str, Any]], lang: str) -> Optional[Dict[str, Any]]:
        text = message.lower().strip()
        # numeric selection
        num_map = {
            "1": 0, "số 1": 0, "so 1": 0, "đầu tiên": 0, "first": 0,
            "2": 1, "số 2": 1, "so 2": 1, "thứ hai": 1, "second": 1,
            "3": 2, "số 3": 2, "so 3": 2, "thứ ba": 2, "third": 2,
        }
        for k, idx in num_map.items():
            if k in text and idx < len(recommendations):
                return recommendations[idx]
        # name match
        for rec in recommendations:
            name = (rec.get("name") or "").lower()
            if name and name in text:
                return rec
        return None

    def _compose_summary_message(self, state: Dict[str, Any], lang: str) -> str:
        if lang == "vi":
            return (
                f"Đặt bàn tại: {state.get('restaurant') or 'Chưa rõ'}; "
                f"Số người: {state.get('party_size') or 'Chưa rõ'}; "
                f"Thời gian: {state.get('time') or 'Chưa rõ'}; "
                f"Ghi chú: {state.get('special_request') or ''}"
            )
        else:
            return (
                f"Booking at: {state.get('restaurant') or 'N/A'}; "
                f"Party size: {state.get('party_size') or 'N/A'}; "
                f"Time: {state.get('time') or 'N/A'}; "
                f"Notes: {state.get('special_request') or ''}"
            )

    def _compose_next_question(self, state: Dict[str, Any], missing: Tuple[str, ...], lang: str) -> str:
        # Prefer LLM suggested question only if aligned with next target field
        if state.get("next_ask") and missing:
            target = missing[0]
            if self._is_ask_aligned(state["next_ask"], target, lang):
                return state["next_ask"]

        # Ask in priority order
        if missing:
            first = missing[0]
            if lang == "vi":
                prompts = {
                    "restaurant": "Bạn muốn đặt ở NHÀ HÀNG/ĐỊA ĐIỂM nào?",
                    "party_size": "Bạn đi MẤY NGƯỜI vậy?",
                    "time": "Bạn muốn đặt vào THỜI GIAN nào (ví dụ: 19:00 tối nay)?",
                    "name": "Bạn vui lòng cho mình biết HỌ TÊN để mình ghi nhận đặt chỗ.",
                    "phone": "Bạn vui lòng cho mình xin SỐ ĐIỆN THOẠI để tiện liên hệ xác nhận nhé.",
                    "email": "Bạn vui lòng cho mình EMAIL để gửi xác nhận đặt chỗ.",
                }
            else:
                prompts = {
                    "restaurant": "Which RESTAURANT/PLACE would you like to book?",
                    "party_size": "For HOW MANY people?",
                    "time": "What TIME would you like (e.g., 7:00 PM tonight)?",
                    "name": "Please tell me your FULL NAME to record the reservation.",
                    "phone": "Please share your PHONE NUMBER for confirmation.",
                    "email": "Please provide your EMAIL to receive confirmation.",
                }
            return prompts.get(first, prompts["restaurant"])  # safe default

        # If everything in priority list is filled but not confirmed yet
        if lang == "vi":
            to_fill = []
            if not state.get("restaurant"):
                to_fill.append("nhà hàng bạn muốn đặt")
            if not state.get("party_size"):
                to_fill.append("số người")
            if not state.get("time"):
                to_fill.append("thời gian")
            if to_fill:
                return "Mình có thể biết " + ", ".join(to_fill) + " không? Bạn có thể trả lời tự nhiên."
            summary = self._compose_summary_message(state, lang)
            return f"Mình đã ghi nhận: {summary}. Bạn nhập 'chốt' hoặc 'xác nhận' để gửi yêu cầu nhé."
        else:
            to_fill = []
            if not state.get("restaurant"):
                to_fill.append("restaurant name")
            if not state.get("party_size"):
                to_fill.append("party size")
            if not state.get("time"):
                to_fill.append("time")
            if to_fill:
                return "Could you tell me the " + ", ".join(to_fill) + "? You can answer naturally."
            summary = self._compose_summary_message(state, lang)
            return f"I have: {summary}. Type 'confirm' to submit."

    def _is_ask_aligned(self, ask: str, target_field: str, lang: str) -> bool:
        text = (ask or "").lower()
        if target_field == "restaurant":
            return any(k in text for k in (["nhà hàng", "địa điểm", "place", "restaurant"]) )
        if target_field == "party_size":
            return any(k in text for k in (["mấy người", "số người", "bao nhiêu người", "how many", "people", "pax"]))
        if target_field == "time":
            return any(k in text for k in (["thời gian", "lúc", "giờ", "time", "when"]))
        if target_field == "name":
            return any(k in text for k in (["tên", "name"]))
        if target_field == "phone":
            return any(k in text for k in (["điện thoại", "số điện thoại", "phone"]))
        if target_field == "email":
            return "email" in text
        return False

    def _next_suggestions(self, missing: Tuple[str, ...], lang: str) -> list[Suggestion]:
        if lang == "vi":
            sug = []
            if not missing:
                sug.append(Suggestion(label="Chốt đơn", detail="Gửi yêu cầu đặt chỗ", action="confirm_booking"))
            else:
                sug.append(Suggestion(label="Bỏ qua", detail="Hủy đặt chỗ", action="cancel_booking"))
            return sug
        else:
            sug = []
            if not missing:
                sug.append(Suggestion(label="Confirm", detail="Submit booking request", action="confirm_booking"))
            else:
                sug.append(Suggestion(label="Cancel", detail="Cancel booking", action="cancel_booking"))
            return sug


