#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, Any, Optional, Tuple
import re
import uuid
import logging

from ..models.schemas import QnAResponse, Suggestion, UserInfoRequest, ServiceResponse
from ..models.platform_models import PlatformContext
from ..core.conversation_memory import ConversationMemory
from ..services.email_service import EmailService
from ..llm.rate_limited_client import RateLimitedLLMClient
from ..agents.service_agent import ServiceAgent

logger = logging.getLogger(__name__)


class BookingAgent:
    """Conversational booking agent that incrementally collects user info and sends emails when confirmed."""

    def __init__(self, memory: ConversationMemory, email_service: Optional[EmailService] = None, llm_client: Optional[RateLimitedLLMClient] = None, service_agent: Optional[ServiceAgent] = None):
        self.memory = memory
        self.email_service = email_service
        
        # Create rate-limited LLM client if not provided
        if llm_client is None:
            from ..llm.open_client import OpenAIClient
            base_llm_client = OpenAIClient()
            self.llm_client = RateLimitedLLMClient(base_llm_client)
        else:
            self.llm_client = llm_client
            
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
                "off_topic_count": 0,  # Count consecutive off-topic questions
                "last_booking_activity": None,  # Track last booking-related activity
            }

            # Use last mentioned place from memory if available
            entities = self.memory.get_entities(conversation_id)
            # Pre-fill contact from user-level entities
            if entities.get("user_name") and not state.get("name"):
                state["name"] = entities.get("user_name")
            if entities.get("user_email") and not state.get("email"):
                state["email"] = entities.get("user_email")
            if entities.get("user_phone") and not state.get("phone"):
                state["phone"] = entities.get("user_phone")

            # Don't automatically set restaurant from memory - let user choose
            # Only suggest if user hasn't specified a restaurant yet
            last_place = entities.get("current_place") or entities.get("last_mentioned_place")
            if last_place and not state.get("restaurant"):
                # Suggest the place but don't auto-select
                state["suggested_place"] = last_place

        # If waiting for a restaurant choice, try to select from recommendations
        if state.get("awaiting_restaurant_selection") and state.get("recommendations"):
            selection = self._extract_restaurant_selection(message, state["recommendations"], platform_context.language.value)
            if selection:
                state["restaurant"] = selection.get("name")
                state["restaurant_id"] = selection.get("id")
                state["awaiting_restaurant_selection"] = False

        # Handle suggested place confirmation
        if state.get("suggested_place") and not state.get("restaurant"):
            # Check if user confirms the suggested place
            if self._is_confirming_suggested_place(message, state["suggested_place"], platform_context.language.value):
                state["restaurant"] = state["suggested_place"]
                state.pop("suggested_place", None)  # Remove suggestion after confirmation
            elif self._is_rejecting_suggested_place(message, platform_context.language.value):
                # User doesn't want the suggested place, clear it and ask for alternatives
                state.pop("suggested_place", None)
                if platform_context.language.value == "vi":
                    answer = "Bạn muốn tìm địa điểm nào khác? Hãy cho mình biết loại ẩm thực hoặc khu vực bạn thích."
                else:
                    answer = "What other places would you like to find? Please let me know what type of cuisine or area you prefer."
                return QnAResponse(
                    type="QnA",
                    answerAI=answer,
                    sources=[],
                    suggestions=[
                        Suggestion(label="Tìm nhà hàng hải sản" if platform_context.language.value == "vi" else "Find seafood restaurants", action="search_services"),
                        Suggestion(label="Tìm nhà hàng Việt Nam" if platform_context.language.value == "vi" else "Find Vietnamese restaurants", action="search_services")
                    ]
                )

        # Extract info and understand user intent using LLM
        llm_result = self._llm_extract_and_plan(state, message, platform_context.language.value)
        
        # Fallback to simple extraction if LLM fails
        if not llm_result:
            extracted = self._extract_booking_info(message, platform_context.language.value)
        else:
            extracted = llm_result
        
        # Update state with extracted information
        for key, value in (extracted or {}).items():
            if value:
                state[key] = value
                # Reset off-topic counter when user provides booking info
                if key in ["name", "email", "phone", "restaurant", "party_size", "time"]:
                    state["off_topic_count"] = 0
                    state["last_booking_activity"] = f"updated_{key}"
        
        # Handle user intent from LLM
        user_intent = state.get("user_intent", "booking_info")
        
        # Heuristic confirmation detection (fallback for LLM)
        confirmation_keywords = ["chốt", "xác nhận", "ok", "được", "chốt thôi", "được rồi", "confirm"]
        if any(keyword in message.lower() for keyword in confirmation_keywords):
            user_intent = "confirmation"
            state["user_intent"] = "confirmation"
        next_action = state.get("next_action", "")
        
        # Check if user wants to pause booking to answer question
        if self._is_pause_booking_request(message, platform_context.language.value) and state.get("pending_question"):
            # User wants to pause booking and answer the pending question
            pending_question = state["pending_question"]
            state.pop("pending_question", None)  # Clear pending question
            state["booking_paused"] = True  # Mark booking as paused
            self._set_booking_state(conversation_id, state)
            
            # Return the pending question for QnA agent to handle
            if platform_context.language.value == "vi":
                answer = f"Được rồi! {pending_question} - Tôi sẽ trả lời ngay. Bây giờ chúng ta tiếp tục đặt bàn nhé!"
            else:
                answer = f"Got it! {pending_question} - I'll answer that. Now let's continue with the booking!"
            
            return QnAResponse(
                type="QnA",
                answerAI=answer,
                sources=[],
                suggestions=[
                    Suggestion(label="Tiếp tục đặt bàn" if platform_context.language.value == "vi" else "Continue booking", 
                              detail="Quay lại booking flow", action="continue_booking")
                ]
            )
        

        
        # Check if user wants to continue booking after pause
        if self._is_continue_booking_request(message, platform_context.language.value) and state.get("booking_paused"):
            state["booking_paused"] = False  # Resume booking
            self._set_booking_state(conversation_id, state)
            
            if platform_context.language.value == "vi":
                answer = "Được rồi, bây giờ chúng ta tiếp tục đặt bàn nhé!"
            else:
                answer = "Alright, let's continue with the booking!"
            
            # Continue with normal booking flow
            # (will fall through to the rest of the logic)
        
        # If we're in modification mode and extracted info, clear the modification flag
        if state.get("modifying_field") and extracted:
            state.pop("modifying_field", None)

        # Handle different user intents intelligently
        if user_intent == "modification":
            # User wants to modify existing booking info
            field_to_modify = self._detect_field_to_modify(message, platform_context.language.value)
            if field_to_modify:
                if platform_context.language.value == "vi":
                    prompts = {
                        "name": "Bạn vui lòng cho mình biết HỌ TÊN mới để mình cập nhật.",
                        "email": "Bạn vui lòng cho mình EMAIL mới để mình cập nhật.",
                        "phone": "Bạn vui lòng cho mình SỐ ĐIỆN THOẠI mới để mình cập nhật.",
                        "restaurant": "Bạn muốn đặt ở NHÀ HÀNG/ĐỊA ĐIỂM nào thay thế?",
                        "party_size": "Bạn đi MẤY NGƯỜI vậy?",
                        "time": "Bạn muốn đặt vào THỜI GIAN nào (ví dụ: 19:00 tối nay)?"
                    }
                    answer = prompts.get(field_to_modify, "Bạn vui lòng cung cấp thông tin mới.")
                else:
                    prompts = {
                        "name": "Please tell me your new FULL NAME to update.",
                        "email": "Please provide your new EMAIL to update.",
                        "phone": "Please share your new PHONE NUMBER to update.",
                        "restaurant": "Which RESTAURANT/PLACE would you like to book instead?",
                        "party_size": "For HOW MANY people?",
                        "time": "What TIME would you like (e.g., 7:00 PM tonight)?"
                    }
                    answer = prompts.get(field_to_modify, "Please provide the new information.")
                
                # Clear the field to be modified
                state[field_to_modify] = None
                state["modifying_field"] = field_to_modify
                self._set_booking_state(conversation_id, state)
                
                return QnAResponse(
                    type="QnA",
                    answerAI=answer,
                    sources=[],
                    suggestions=[Suggestion(label="Bỏ qua" if platform_context.language.value == "vi" else "Cancel", detail="Hủy sửa đổi", action="cancel_booking")]
                )
        
        elif user_intent == "confirmation":
            # User confirms the booking
            state["confirmed"] = True
            state["status"] = "submitted"
            self._set_booking_state(conversation_id, state)
            
            # Prepare booking summary
            booking_summary = f"""
📋 **Thông tin đặt bàn đã xác nhận:**
🏪 Nhà hàng: {state.get('restaurant', 'Chưa xác định')}
👥 Số người: {state.get('party_size', 'Chưa xác định')}
🕐 Thời gian: {state.get('time', 'Chưa xác định')}
👤 Tên: {state.get('name', 'Chưa xác định')}
📧 Email: {state.get('email', 'Chưa xác định')}
📱 SĐT: {state.get('phone', 'Chưa xác định')}
📝 Ghi chú: {state.get('special_request', 'Không có')}
            """.strip()
            
            if platform_context.language.value == "vi":
                answer = f"✅ Đã xác nhận đặt bàn thành công!\n\n{booking_summary}\n\nTôi sẽ gửi email xác nhận cho bạn sớm nhất."
            else:
                answer = f"✅ Booking confirmed successfully!\n\n{booking_summary}\n\nI'll send you a confirmation email shortly."
            
            return QnAResponse(
                type="QnA",
                answerAI=answer,
                sources=[],
                suggestions=[
                    Suggestion(label="Đặt bàn mới" if platform_context.language.value == "vi" else "New booking", 
                              detail="Bắt đầu đặt bàn khác", action="start_booking"),
                    Suggestion(label="Tìm nhà hàng" if platform_context.language.value == "vi" else "Find restaurants", 
                              detail="Tìm kiếm nhà hàng", action="show_services")
                ]
            )
        
        elif user_intent == "pause_booking":
            # User wants to pause booking to answer question
            if state.get("pending_question"):
                pending_question = state["pending_question"]
                state.pop("pending_question", None)
                state["booking_paused"] = True
                self._set_booking_state(conversation_id, state)
                
                if platform_context.language.value == "vi":
                    answer = f"Được rồi! {pending_question} - Tôi sẽ trả lời ngay. Bây giờ chúng ta tiếp tục đặt bàn nhé!"
                else:
                    answer = f"Got it! {pending_question} - I'll answer that. Now let's continue with the booking!"
                
                return QnAResponse(
                    type="QnA",
                    answerAI=answer,
                    sources=[],
                    suggestions=[
                        Suggestion(label="Tiếp tục đặt bàn" if platform_context.language.value == "vi" else "Continue booking", 
                                  detail="Quay lại booking flow", action="continue_booking")
                    ]
                )
        
        elif user_intent == "answer_request":
            # User wants to get answer to pending question
            if state.get("pending_question"):
                pending_question = state["pending_question"]
                state.pop("pending_question", None)
                state["booking_paused"] = True
                self._set_booking_state(conversation_id, state)
                
                # Provide short, direct answer and continue booking
                if platform_context.language.value == "vi":
                    answer = f"Được rồi! {pending_question} - Tôi sẽ trả lời ngay. Bây giờ chúng ta tiếp tục đặt bàn nhé!"
                else:
                    answer = f"Got it! {pending_question} - I'll answer that. Now let's continue with the booking!"
                
                return QnAResponse(
                    type="QnA",
                    answerAI=answer,
                    sources=[],
                    suggestions=[
                        Suggestion(label="Tiếp tục đặt bàn" if platform_context.language.value == "vi" else "Continue booking", 
                                  detail="Quay lại booking flow", action="continue_booking")
                    ]
                )
        
        elif user_intent == "continue_booking":
            # User wants to continue booking after pause
            state["booking_paused"] = False
            state["off_topic_count"] = 0  # Reset off-topic counter when returning to booking
            state["last_booking_activity"] = "continue"
            self._set_booking_state(conversation_id, state)
            
            if platform_context.language.value == "vi":
                answer = "Được rồi, bây giờ chúng ta tiếp tục đặt bàn nhé!"
            else:
                answer = "Alright, let's continue with the booking!"
            
            # Continue with normal booking flow
            # (will fall through to the rest of the logic)
        
        elif user_intent == "start_booking":
            # User wants to start a new booking
            # Check if we have previous collected info
            collected_info = state.get("collected_info", {})
            
            # Initialize new booking state with previous info if available
            state = {
                "status": "collecting",
                "name": collected_info.get("name"),
                "email": collected_info.get("email"),
                "phone": collected_info.get("phone"),
                "restaurant": collected_info.get("restaurant"),
                "party_size": collected_info.get("party_size"),
                "time": collected_info.get("time"),
                "special_request": None,
                "confirmed": False,
                "off_topic_count": 0,
                "last_booking_activity": "started",
            }
            self._set_booking_state(conversation_id, state)
            
            if platform_context.language.value == "vi":
                answer = "Được rồi! Bắt đầu đặt bàn mới. Bạn muốn đặt bàn ở đâu?"
            else:
                answer = "Alright! Starting a new booking. Where would you like to book?"
            
            return QnAResponse(
                type="QnA",
                answerAI=answer,
                sources=[],
                suggestions=[
                    Suggestion(label="Tìm nhà hàng" if platform_context.language.value == "vi" else "Find restaurants", 
                              detail="Tìm kiếm nhà hàng", action="show_services")
                ]
            )
        
        elif user_intent == "other_topic":
            # User is asking about something else
            # Increment off-topic counter
            state["off_topic_count"] = state.get("off_topic_count", 0) + 1
            
            # Check if we should auto-cancel booking after 3 off-topic questions
            if state["off_topic_count"] >= 3:
                # Auto-cancel booking but preserve collected info
                if platform_context.language.value == "vi":
                    answer = f"Tôi thấy bạn đang hỏi nhiều câu hỏi khác. Tôi sẽ hủy việc đặt bàn và lưu thông tin đã có. Bạn có thể bắt đầu đặt bàn lại bất cứ lúc nào."
                else:
                    answer = f"I notice you're asking many other questions. I'll cancel the booking and save the information we've collected. You can start booking again anytime."
                
                # Reset booking state but keep collected info
                collected_info = {
                    "name": state.get("name"),
                    "email": state.get("email"),
                    "phone": state.get("phone"),
                    "restaurant": state.get("restaurant"),
                    "party_size": state.get("party_size"),
                    "time": state.get("time"),
                }
                
                # Clear booking state
                state = {
                    "status": "cancelled",
                    "off_topic_count": 0,
                    "last_booking_activity": None,
                    "collected_info": collected_info,  # Save for future use
                }
                self._set_booking_state(conversation_id, state)
                
                return QnAResponse(
                    type="QnA",
                    answerAI=answer,
                    sources=[],
                    suggestions=[
                        Suggestion(label="Đặt bàn lại" if platform_context.language.value == "vi" else "Book again", 
                                  detail="Bắt đầu đặt bàn mới", action="start_booking"),
                        Suggestion(label="Tìm nhà hàng" if platform_context.language.value == "vi" else "Find restaurants", 
                                  detail="Tìm kiếm nhà hàng", action="show_services")
                    ]
                )
            
            # Normal other_topic handling
            if platform_context.language.value == "vi":
                answer = f"Tôi hiểu bạn đang hỏi về chủ đề khác. Bạn có muốn tôi trả lời câu hỏi này trước, sau đó quay lại việc đặt bàn không? (Đã hỏi {state['off_topic_count']}/3 câu ngoài lề)"
                suggestions = [
                    Suggestion(label="Có, trả lời câu hỏi trước", detail="Tạm dừng booking để trả lời", action="pause_booking_answer_question"),
                    Suggestion(label="Không, tiếp tục đặt bàn", detail="Bỏ qua câu hỏi, tiếp tục booking", action="continue_booking")
                ]
            else:
                answer = f"I understand you're asking about something else. Would you like me to answer this question first, then return to booking? ({state['off_topic_count']}/3 off-topic questions)"
                suggestions = [
                    Suggestion(label="Yes, answer the question first", detail="Pause booking to answer", action="pause_booking_answer_question"),
                    Suggestion(label="No, continue booking", detail="Skip question, continue booking", action="continue_booking")
                ]
            
            # Store the question for later answering
            state["pending_question"] = message
            self._set_booking_state(conversation_id, state)
            
            return QnAResponse(
                type="QnA",
                answerAI=answer,
                sources=[],
                suggestions=suggestions
            )
        
        # Legacy modification detection (fallback)
        if self._is_modification_request(message, platform_context.language.value):
            # User wants to modify existing booking info
            field_to_modify = self._detect_field_to_modify(message, platform_context.language.value)
            if field_to_modify:
                if platform_context.language.value == "vi":
                    prompts = {
                        "name": "Bạn vui lòng cho mình biết HỌ TÊN mới để mình cập nhật.",
                        "email": "Bạn vui lòng cho mình EMAIL mới để mình cập nhật.",
                        "phone": "Bạn vui lòng cho mình SỐ ĐIỆN THOẠI mới để mình cập nhật.",
                        "restaurant": "Bạn muốn đặt ở NHÀ HÀNG/ĐỊA ĐIỂM nào thay thế?",
                        "party_size": "Bạn đi MẤY NGƯỜI vậy?",
                        "time": "Bạn muốn đặt vào THỜI GIAN nào (ví dụ: 19:00 tối nay)?"
                    }
                    answer = prompts.get(field_to_modify, "Bạn vui lòng cung cấp thông tin mới.")
                else:
                    prompts = {
                        "name": "Please tell me your new FULL NAME to update.",
                        "email": "Please provide your new EMAIL to update.",
                        "phone": "Please share your new PHONE NUMBER to update.",
                        "restaurant": "Which RESTAURANT/PLACE would you like to book instead?",
                        "party_size": "For HOW MANY people?",
                        "time": "What TIME would you like (e.g., 7:00 PM tonight)?"
                    }
                    answer = prompts.get(field_to_modify, "Please provide the new information.")
                
                # Clear the field to be modified
                state[field_to_modify] = None
                state["modifying_field"] = field_to_modify
                self._set_booking_state(conversation_id, state)
                
                return QnAResponse(
                    type="QnA",
                    answerAI=answer,
                    sources=[],
                    suggestions=[Suggestion(label="Bỏ qua" if platform_context.language.value == "vi" else "Cancel", detail="Hủy sửa đổi", action="cancel_booking")]
                )

        # Check if user is asking about other topics while in booking flow
        # BUT only if we didn't extract any booking information from the message
        if not extracted and self._is_asking_other_topics(message, platform_context.language.value):
            # User is asking about something else, not booking info
            # We should answer their question first, then ask if they want to continue booking
            if platform_context.language.value == "vi":
                answer = "Tôi hiểu bạn đang hỏi về chủ đề khác. Bạn có muốn tôi trả lời câu hỏi này trước, sau đó quay lại việc đặt bàn không?"
                suggestions = [
                    Suggestion(label="Có, trả lời câu hỏi trước", detail="Tạm dừng booking để trả lời", action="pause_booking_answer_question"),
                    Suggestion(label="Không, tiếp tục đặt bàn", detail="Bỏ qua câu hỏi, tiếp tục booking", action="continue_booking")
                ]
            else:
                answer = "I understand you're asking about something else. Would you like me to answer this question first, then return to booking?"
                suggestions = [
                    Suggestion(label="Yes, answer the question first", detail="Pause booking to answer", action="pause_booking_answer_question"),
                    Suggestion(label="No, continue booking", detail="Skip question, continue booking", action="continue_booking")
                ]
            
            return QnAResponse(
                type="QnA",
                answerAI=answer,
                sources=[],
                suggestions=suggestions
            )

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
                    # Build response asking user to choose - keep as QnA type for consistency
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
                    
                    # Return QnA response with service sources for consistency
                    return QnAResponse(
                        type="QnA",  # Keep consistent with booking flow
                        answerAI=answer,
                        sources=services_resp.sources or [],
                        suggestions=suggestions
                    )

        # Check if user has a suggested place but hasn't confirmed yet
        if state.get("suggested_place") and not state.get("restaurant"):
            # Ask user to confirm the suggested place
            if platform_context.language.value == "vi":
                answer = f"Bạn có muốn đặt bàn tại {state['suggested_place']} không?"
                suggestions = [
                    Suggestion(label=f"Có, đặt tại {state['suggested_place']}", detail="Xác nhận đặt bàn", action="confirm_suggested_place"),
                    Suggestion(label="Không, tìm địa điểm khác", detail="Tìm kiếm địa điểm khác", action="search_other_places")
                ]
            else:
                answer = f"Would you like to book a table at {state['suggested_place']}?"
                suggestions = [
                    Suggestion(label=f"Yes, book at {state['suggested_place']}", detail="Confirm booking", action="confirm_suggested_place"),
                    Suggestion(label="No, find other places", detail="Search for other places", action="search_other_places")
                ]
            
            return QnAResponse(
                type="QnA",
                answerAI=answer,
                sources=[],
                suggestions=suggestions
            )

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
        
        # Use LLM-generated question if available and appropriate
        if state.get("next_question") and user_intent == "booking_info":
            ask_text = state["next_question"]
        else:
            # If we just finished modifying a field, show updated summary
            if state.get("modifying_field") is None and any(extracted.values()):
                # We just received new info, show updated summary
                summary = self._compose_summary_message(state, platform_context.language.value)
                if platform_context.language.value == "vi":
                    ask_text = f"Đã cập nhật thông tin: {summary}. Bạn có muốn sửa gì thêm không?"
                else:
                    ask_text = f"Updated information: {summary}. Do you want to modify anything else?"
            else:
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
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        if email_match:
            result["email"] = email_match.group(0)

        # Phone (simple VN format detection)
        phone_match = re.search(r"\+?\d{9,13}", text.replace(" ", ""))
        if phone_match:
            result["phone"] = phone_match.group(0)
        
        # Name detection for simple cases
        # If we have email/phone but no name, try to extract name from the beginning
        if (result["email"] or result["phone"]) and not result["name"]:
            # Look for a word before email/phone that could be a name
            words = text.split()
            for i, word in enumerate(words):
                # Check if this word is before email or phone
                if (result["email"] and result["email"] in word) or (result["phone"] and result["phone"] in word):
                    # Check if there's a word before this that could be a name
                    if i > 0 and len(words[i-1]) >= 2 and words[i-1].isalpha():
                        result["name"] = words[i-1].strip()
                        break

        # Party size (people)
        people_match = re.search(r"(\d+)\s*(người|nguoi|pax|people)", text.lower())
        if people_match:
            result["party_size"] = people_match.group(1)
        else:
            # Try to extract party size from context using LLM
            party_size_from_context = self._extract_party_size_from_context(text, lang)
            if party_size_from_context:
                result["party_size"] = party_size_from_context

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
        
        # Simple name detection (if no email/phone in the same message, treat single word as name)
        if not result["name"] and not result["email"] and not result["phone"]:
            # Check if message is just a single word that looks like a name
            words = text.strip().split()
            if len(words) == 1 and len(words[0]) >= 2 and words[0].isalpha():
                result["name"] = words[0].strip()

        return result

    def _llm_extract_and_plan(self, state: Dict[str, Any], message: str, lang: str) -> Optional[Dict[str, Optional[str]]]:
        """Use LLM to intelligently extract booking fields and plan next actions"""
        try:
            if not self.llm_client or not self.llm_client.is_configured():
                return None

            # Build comprehensive state snapshot for the LLM
            snapshot = {
                "name": state.get("name"),
                "email": state.get("email"), 
                "phone": state.get("phone"),
                "restaurant": state.get("restaurant"),
                "party_size": state.get("party_size"),
                "time": state.get("time"),
                "special_request": state.get("special_request"),
                "modifying_field": state.get("modifying_field"),
                "status": state.get("status", "collecting")
            }

            if lang == "vi":
                system = """Bạn là trợ lý đặt chỗ thông minh. Phân tích tin nhắn người dùng và trạng thái hiện tại để:

1. EXTRACT thông tin mới từ tin nhắn
2. UNDERSTAND context và intent của người dùng
3. PLAN câu hỏi tiếp theo phù hợp

Trả về JSON với format:
{
  "extracted_info": {
    "name": "tên nếu có",
    "email": "email nếu có", 
    "phone": "số điện thoại nếu có",
    "restaurant": "nhà hàng nếu có",
    "party_size": "số người nếu có",
    "time": "thời gian nếu có",
    "special_request": "yêu cầu đặc biệt nếu có"
  },
  "user_intent": "booking_info|modification|confirmation|other_topic",
  "next_action": "ask_name|ask_email|ask_phone|ask_restaurant|ask_party_size|ask_time|confirm_booking|handle_other",
  "next_question": "câu hỏi tiếp theo phù hợp",
  "confidence": "high|medium|low"
}

Lưu ý:
- Nếu user nói "với anh Quyền và Sếp Hải" → party_size = "3"
- Nếu user nói "tuan@gmail.com" → email = "tuan@gmail.com"
- Nếu user nói "sửa email" → user_intent = "modification", next_action = "ask_email"
- Nếu user nói "chốt" → user_intent = "confirmation"
- Nếu user hỏi về chủ đề khác (lịch sử, văn hóa, địa điểm, v.v.) → user_intent = "other_topic"
- Nếu user nói "có", "được", "ok" sau khi được hỏi có muốn trả lời câu hỏi trước không → user_intent = "pause_booking"
- Nếu user nói "trả lời đi", "ok trả lời" → user_intent = "answer_request"
- Nếu user nói "tiếp tục", "quay lại đặt bàn" → user_intent = "continue_booking"
- Nếu user nói "đặt bàn lại", "bắt đầu đặt bàn" → user_intent = "start_booking"
- Nếu user nói "chốt", "xác nhận", "ok", "được", "chốt thôi", "được rồi" → user_intent = "confirmation"

Chỉ trả về JSON, không có text khác."""
            else:
                system = """You are an intelligent booking assistant. Analyze the user message and current state to:

1. EXTRACT new information from the message
2. UNDERSTAND user context and intent  
3. PLAN appropriate next question

Return JSON with format:
{
  "extracted_info": {
    "name": "name if present",
    "email": "email if present",
    "phone": "phone if present", 
    "restaurant": "restaurant if present",
    "party_size": "number of people if present",
    "time": "time if present",
    "special_request": "special request if present"
  },
  "user_intent": "booking_info|modification|confirmation|other_topic",
  "next_action": "ask_name|ask_email|ask_phone|ask_restaurant|ask_party_size|ask_time|confirm_booking|handle_other",
  "next_question": "appropriate next question",
  "confidence": "high|medium|low"
}

Notes:
- If user says "with John and Mary" → party_size = "3"
- If user says "john@gmail.com" → email = "john@gmail.com"
- If user says "change email" → user_intent = "modification", next_action = "ask_email"
- If user says "confirm" → user_intent = "confirmation"
- If user asks about other places → user_intent = "other_topic"

Return JSON only, no other text."""

            user = f"Current booking state: {snapshot}\nUser message: '{message}'\nAnalyze and return JSON."

            prompt = f"System: {system}\n\nUser: {user}"
            out = self.llm_client.generate_response_sync(prompt, max_tokens=300, temperature=0.1)
            if not out:
                return None

            # Extract JSON
            import json, re
            m = re.search(r"\{[\s\S]*\}", out)
            if not m:
                return None
            data = json.loads(m.group(0))

            # Store LLM insights in state
            if data.get("next_question"):
                state["next_question"] = data["next_question"]
            if data.get("user_intent"):
                state["user_intent"] = data["user_intent"]
            if data.get("next_action"):
                state["next_action"] = data["next_action"]

            # Extract and return new information
            extracted_info = data.get("extracted_info") or {}
            extracted: Dict[str, Optional[str]] = {}
            for key in ["name", "email", "phone", "restaurant", "party_size", "time", "special_request"]:
                val = extracted_info.get(key)
                if isinstance(val, str) and val.strip():
                    extracted[key] = val.strip()

            return extracted or None
        except Exception as e:
            # Fallback to simple extraction
            return None

    def _is_discovery_message(self, message: str, lang: str) -> bool:
        m = message.lower()
        vi_triggers = ["tìm", "gợi ý", "gần", "xung quanh", "khu vực", "cầu rồng", "bán đảo sơn trà", "biển", "near", "around"]
        en_triggers = ["find", "suggest", "near", "around", "area"]
        triggers = vi_triggers if lang == "vi" else en_triggers
        return any(t in m for t in triggers)

    def _extract_restaurant_selection(self, message: str, recommendations: list[Dict[str, Any]], lang: str) -> Optional[Dict[str, Any]]:
        """Extract restaurant selection from user message using LLM"""
        try:
            if not self.llm_client or not self.llm_client.is_configured():
                # Fallback to keyword-based selection
                return self._extract_restaurant_selection_keyword(message, recommendations, lang)
            
            # Use LLM to analyze restaurant selection
            if lang == "vi":
                prompt = f"""Phân tích câu hỏi của người dùng và xác định họ muốn chọn nhà hàng nào từ danh sách gợi ý.

Câu hỏi: "{message}"

Danh sách nhà hàng gợi ý:
{self._format_recommendations_for_prompt(recommendations, lang)}

Trả về JSON:
{{"selected_index": số thứ tự (1,2,3...), "selected_name": "tên nhà hàng", "confidence": "cao/trung bình/thấp", "reason": "lý do"}}

Nếu không chọn được nhà hàng nào, trả về:
{{"selected_index": null, "selected_name": null, "confidence": "thấp", "reason": "không xác định được"}}

Chỉ trả về JSON, không có text khác."""
            else:
                prompt = f"""Analyze the user's question and determine which restaurant they want to select from the recommendation list.

Question: "{message}"

Restaurant recommendations:
{self._format_recommendations_for_prompt(recommendations, lang)}

Return JSON:
{{"selected_index": number (1,2,3...), "selected_name": "restaurant name", "confidence": "high/medium/low", "reason": "reason"}}

If no restaurant can be determined, return:
{{"selected_index": null, "selected_name": null, "confidence": "low", "reason": "cannot determine"}}

Return JSON only, no other text."""
            
            response = self.llm_client.generate_response_sync(prompt, max_tokens=150, temperature=0.1)
            
            if response:
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    selected_index = data.get("selected_index")
                    
                    if selected_index and isinstance(selected_index, int) and 1 <= selected_index <= len(recommendations):
                        # Convert to 0-based index
                        actual_index = selected_index - 1
                        return recommendations[actual_index]
            
            # Fallback to keyword-based selection
            return self._extract_restaurant_selection_keyword(message, recommendations, lang)
            
        except Exception as e:
            logger.error(f"Error in LLM restaurant selection: {e}")
            # Fallback to keyword-based selection
            return self._extract_restaurant_selection_keyword(message, recommendations, lang)
    
    def _extract_restaurant_selection_keyword(self, message: str, recommendations: list[Dict[str, Any]], lang: str) -> Optional[Dict[str, Any]]:
        """Keyword-based fallback for restaurant selection"""
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
    
    def _format_recommendations_for_prompt(self, recommendations: list[Dict[str, Any]], lang: str) -> str:
        """Format recommendations for LLM prompt"""
        formatted = []
        for i, rec in enumerate(recommendations, 1):
            name = rec.get("name", "")
            formatted.append(f"{i}. {name}")
        return "\n".join(formatted)

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

            # Try LLM to craft a short, natural, personalized question
            llm_q = self._llm_personalized_next_question(state, first, lang)
            if llm_q:
                return llm_q

            # Fallback static prompts with light personalization
            prefix = self._personalized_prefix(state, lang)
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
            core = prompts.get(first, prompts["restaurant"])  # safe default
            return (f"{prefix} {core}" if prefix else core)

        # If everything in priority list is filled but not confirmed yet
        summary = self._compose_summary_message(state, lang)
        if lang == "vi":
            prefix = self._personalized_prefix(state, lang)
            core = f"Mình đã ghi nhận: {summary}. Bạn nhập 'chốt' hoặc 'xác nhận' để gửi yêu cầu nhé."
            return (f"{prefix} {core}" if prefix else core)
        else:
            prefix = self._personalized_prefix(state, lang)
            core = f"I have: {summary}. Type 'confirm' to submit."
            return (f"{prefix} {core}" if prefix else core)

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

    def _is_modification_request(self, message: str, lang: str) -> bool:
        """Detect if user wants to modify existing booking information"""
        text = message.lower().strip()
        
        if lang == "vi":
            modification_keywords = [
                "sửa", "sửa lại", "thay đổi", "đổi", "cập nhật", "update",
                "sai", "nhầm", "không đúng", "không phải", "không phải vậy",
                "cho tôi sửa", "cho tôi đổi", "cho tôi thay đổi"
            ]
        else:
            modification_keywords = [
                "change", "modify", "update", "edit", "correct", "fix",
                "wrong", "incorrect", "not right", "not correct",
                "let me change", "let me modify", "let me update"
            ]
        
        return any(keyword in text for keyword in modification_keywords)

    def _detect_field_to_modify(self, message: str, lang: str) -> Optional[str]:
        """Detect which field the user wants to modify"""
        text = message.lower().strip()
        
        if lang == "vi":
            field_keywords = {
                "name": ["tên", "họ tên", "tên đầy đủ"],
                "email": ["email", "mail", "e-mail"],
                "phone": ["số điện thoại", "điện thoại", "phone", "số phone", "số"],
                "restaurant": ["nhà hàng", "địa điểm", "quán", "restaurant"],
                "party_size": ["số người", "mấy người", "bao nhiêu người", "người"],
                "time": ["thời gian", "giờ", "lúc", "time"]
            }
        else:
            field_keywords = {
                "name": ["name", "full name"],
                "email": ["email", "mail", "e-mail"],
                "phone": ["phone", "phone number", "number", "telephone"],
                "restaurant": ["restaurant", "place", "location"],
                "party_size": ["people", "number of people", "how many"],
                "time": ["time", "when", "hour"]
            }
        
        for field, keywords in field_keywords.items():
            if any(keyword in text for keyword in keywords):
                return field
        
        return None

    def _extract_party_size_from_context(self, text: str, lang: str) -> Optional[str]:
        """Extract party size from context using LLM"""
        try:
            if not self.llm_client or not self.llm_client.is_configured():
                return None
            
            if lang == "vi":
                prompt = f"""Phân tích câu sau và xác định số người sẽ đi ăn/đặt bàn.

Câu: "{text}"

Các trường hợp:
- "tôi đi với anh Quyền, Sếp Hải và thầy Tuấn" = 4 người (tôi + anh Quyền + Sếp Hải + thầy Tuấn)
- "đi cùng vợ và 2 con" = 4 người (tôi + vợ + 2 con)
- "với bạn gái" = 2 người (tôi + bạn gái)
- "cùng team 5 người" = 6 người (tôi + team 5 người)
- "đi một mình" = 1 người

Trả về JSON:
{{"party_size": "số người (chỉ số)", "reason": "lý do"}}

Nếu không xác định được, trả về:
{{"party_size": null, "reason": "không xác định được"}}

Chỉ trả về JSON, không có text khác."""
            else:
                prompt = f"""Analyze the following sentence and determine the number of people for dining/booking.

Sentence: "{text}"

Cases:
- "I'm going with John and Mary" = 3 people (me + John + Mary)
- "with my wife and 2 kids" = 4 people (me + wife + 2 kids)
- "with my girlfriend" = 2 people (me + girlfriend)
- "with team of 5" = 6 people (me + team of 5)
- "going alone" = 1 person

Return JSON:
{{"party_size": "number (string)", "reason": "reason"}}

If cannot determine, return:
{{"party_size": null, "reason": "cannot determine"}}

Return JSON only, no other text."""
            
            response = self.llm_client.generate_response_sync(prompt, max_tokens=100, temperature=0.1)
            
            if response:
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    party_size = data.get("party_size")
                    if party_size and isinstance(party_size, str) and party_size.isdigit():
                        return party_size
            
            return None
            
        except Exception as e:
            # Fallback to simple keyword detection
            return self._extract_party_size_keyword(text, lang)
    
    def _extract_party_size_keyword(self, text: str, lang: str) -> Optional[str]:
        """Keyword-based fallback for party size extraction"""
        text_lower = text.lower().strip()
        
        # Common patterns
        patterns = [
            (r"một mình|alone|solo", "1"),
            (r"với (\w+)|with (\w+)", "2"),  # with someone = 2 people
            (r"cùng (\w+)|together with (\w+)", "2"),
            (r"và (\w+)|and (\w+)", "2"),  # and someone = at least 2
        ]
        
        for pattern, default_size in patterns:
            if re.search(pattern, text_lower):
                return default_size
        
        return None

    def _is_pause_booking_request(self, message: str, lang: str) -> bool:
        """Detect if user wants to pause booking to answer question"""
        text = message.lower().strip()
        
        if lang == "vi":
            pause_keywords = ["có", "được", "ok", "okie", "oke", "trả lời trước", "trả lời câu hỏi trước"]
        else:
            pause_keywords = ["yes", "ok", "okay", "answer first", "answer question first"]
        
        return any(keyword in text for keyword in pause_keywords)

    def _is_continue_booking_request(self, message: str, lang: str) -> bool:
        """Detect if user wants to continue booking after pause"""
        text = message.lower().strip()
        
        if lang == "vi":
            continue_keywords = ["tiếp tục", "tiếp tục đặt bàn", "quay lại", "quay lại đặt bàn", "đặt bàn tiếp"]
        else:
            continue_keywords = ["continue", "continue booking", "back to booking", "resume booking"]
        
        return any(keyword in text for keyword in continue_keywords)

    def _is_answer_request(self, message: str, lang: str) -> bool:
        """Detect if user wants to get answer to pending question"""
        text = message.lower().strip()
        
        if lang == "vi":
            answer_keywords = ["trả lời đi", "trả lời", "ok trả lời", "được trả lời", "trả lời luôn"]
        else:
            answer_keywords = ["answer", "answer it", "ok answer", "answer now", "answer please"]
        
        return any(keyword in text for keyword in answer_keywords)

    def _personalized_prefix(self, state: Dict[str, Any], lang: str) -> str:
        name = (state.get("name") or "").strip()
        if not name:
            return ""
        # Prefer last token as first-name style
        first_name = name.split()[-1]
        if lang == "vi":
            return f"Chào {first_name},"
        return f"Hi {first_name},"

    def _llm_personalized_next_question(self, state: Dict[str, Any], target_field: str, lang: str) -> Optional[str]:
        try:
            if not self.llm_client or not self.llm_client.is_configured():
                return None
            known = {
                "name": state.get("name"),
                "email": state.get("email"),
                "phone": state.get("phone"),
                "restaurant": state.get("restaurant"),
                "party_size": state.get("party_size"),
                "time": state.get("time"),
            }
            if lang == "vi":
                system = (
                    "Bạn là trợ lý đặt chỗ thân thiện. Viết MỘT câu hỏi ngắn, tự nhiên bằng tiếng Việt để hỏi trường còn thiếu:"
                    f" {target_field}. Nếu đã biết tên, hãy xưng hô thân thiện (ví dụ: 'Chào Tuấn, ...'). "
                    "Chỉ trả về đúng câu hỏi, không thêm ký hiệu hay giải thích."
                )
                user = f"Thông tin đã biết: {known}. Hãy tạo câu hỏi."
            else:
                system = (
                    "You are a friendly booking assistant. Write ONE short, natural question in English to ask for the missing field:"
                    f" {target_field}. If name is known, greet by first name (e.g., 'Hi John, ...'). "
                    "Return the question only."
                )
                user = f"Known info: {known}. Generate question."
            prompt = f"System: {system}\n\nUser: {user}"
            out = self.llm_client.generate_response_sync(prompt, max_tokens=60, temperature=0.3)
            if out:
                q = out.strip().strip('"')
                # Basic guard: ensure it references the target field semantically
                if self._is_ask_aligned(q, target_field, lang):
                    return q
            return None
        except Exception:
            return None

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

    def _is_confirming_suggested_place(self, message: str, suggested_place: str, lang: str) -> bool:
        text = message.lower().strip()
        if lang == "vi":
            return any(w in text for w in ["đồng ý", "ok", "okie", "oke", "gửi đi", "gửi", "hoàn tất", "chốt"])
        else:
            return any(w in text for w in ["confirm", "ok", "okay", "send", "proceed", "done", "finish"])

    def _is_rejecting_suggested_place(self, message: str, lang: str) -> bool:
        text = message.lower().strip()
        if lang == "vi":
            return any(w in text for w in ["không", "không muốn", "không muốn đi", "không muốn đặt", "không muốn đặt chỗ", "bỏ qua", "hủy"])
        else:
            return any(w in text for w in ["no", "no thanks", "no thanks, cancel", "no thanks, booking", "no thanks, reservation", "cancel", "hủy"])

    def _is_asking_other_topics(self, message: str, lang: str) -> bool:
        """Detect if user is asking about other topics while in booking flow using LLM"""
        try:
            if not self.llm_client or not self.llm_client.is_configured():
                # Fallback to keyword-based detection
                return self._is_asking_other_topics_keyword(message, lang)
            
            # Use LLM to analyze if the message is about other topics
            if lang == "vi":
                prompt = f"""Phân tích câu hỏi sau và xác định xem người dùng có đang hỏi về chủ đề khác (không phải thông tin đặt bàn, đặt chỗ) hay không.

Câu hỏi: "{message}"

Các chủ đề KHÁC bao gồm:
- Thông tin du lịch, địa điểm, bảo tàng, di tích
- Ẩm thực, văn hóa, lịch sử
- Thời tiết, giao thông, phương tiện
- Giá cả, giờ mở cửa, địa chỉ
- Các dịch vụ khác (khách sạn, tour, shopping)

Thông tin đặt bàn bao gồm:
- Tên, email, số điện thoại
- Số người, thời gian, ngày tháng
- Nhà hàng, địa điểm cụ thể
- Ghi chú, yêu cầu đặc biệt
** Nếu chưa biết hoặc chưa đủ thông tin để xác định đúng hành vi, mong muốn của người dùng hãy hỏi lại.
    -Ví dụ: Đang đặt bàn, nhưng người dùng lại cắt ngang để hỏi chuyện khác thì hảy trả lời cho họ rồi hỏi tiếp về thông tin đang thiếu.
            Nếu dựa vào ngữ cảnh mà còn mơ hồ thì cứ hỏi lại nhưng cố gắng đừng hỏi lại mà hãy suy nghĩ thật kĩ trước
Trả về JSON:
{{"is_other_topic": true/false, "reason": "lý do"}}

Chỉ trả về JSON, không có text khác."""
            else:
                prompt = f"""Analyze the following question and determine if the user is asking about other topics (not booking information).

Question: "{message}"

OTHER topics include:
- Travel information, attractions, museums, heritage sites
- Food, culture, history
- Weather, transportation, vehicles
- Prices, opening hours, addresses
- Other services (hotels, tours, shopping)

Booking information includes:
- Name, email, phone number
- Number of people, time, date
- Restaurant, specific location
- Notes, special requests

Return JSON:
{{"is_other_topic": true/false, "reason": "reason"}}

Return JSON only, no other text."""
            
            response = self.llm_client.generate_response_sync(prompt, max_tokens=100, temperature=0.1)
            
            if response:
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    return data.get("is_other_topic", False)
            
            # Fallback to keyword-based detection
            return self._is_asking_other_topics_keyword(message, lang)
            
        except Exception as e:
            # logger.error(f"Error in LLM topic detection: {e}") # This line was removed as per the new_code, so it's removed here.
            # Fallback to keyword-based detection
            return self._is_asking_other_topics_keyword(message, lang)
    
    def _is_asking_other_topics_keyword(self, message: str, lang: str) -> bool:
        """Keyword-based fallback for topic detection"""
        text = message.lower().strip()
        
        # Check for question patterns
        question_indicators = ["là gì", "tại sao", "như thế nào", "bao giờ", "ai", "cái gì", "what", "why", "how", "when", "who", "where"]
        if any(indicator in text for indicator in question_indicators):
            return True
        
        # Check for non-booking topics
        non_booking_topics = [
            # Tourist attractions
            "bảo tàng", "museum", "di tích", "heritage", "di sản", "attraction", "điểm tham quan",
            # General info
            "giờ mở cửa", "opening hours", "giá vé", "ticket price", "địa chỉ", "address",
            # Culture/food info
            "ẩm thực", "cuisine", "văn hóa", "culture", "lịch sử", "history",
            # Weather/transport
            "thời tiết", "weather", "giao thông", "transport", "xe buýt", "bus",
            # Other services
            "khách sạn", "hotel", "tour", "du lịch", "travel", "shopping", "mua sắm"
        ]
        
        if any(topic in text for topic in non_booking_topics):
            return True
        
        # Check for explicit statements about asking other things
        other_question_indicators = [
            "cho hỏi", "hỏi thêm", "hỏi về", "ask about", "ask for", "wonder about",
            "tôi muốn biết", "i want to know", "i would like to know"
        ]
        
        if any(indicator in text for indicator in other_question_indicators):
            return True
        
        return False


