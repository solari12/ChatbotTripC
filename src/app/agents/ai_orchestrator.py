#!/usr/bin/env python3
"""
AI Agent Orchestrator - LangGraph-based workflow for TripC.AI Chatbot
Replaces the traditional orchestrator with a visual workflow
"""

from typing import Dict, Any, Optional, TypedDict
import re
from langgraph.graph import StateGraph, END

from ..models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType
from ..models.schemas import ChatRequest, ChatResponse, QnAResponse, Suggestion
from ..agents.qna_agent import QnAAgent
from ..agents.service_agent import ServiceAgent
from ..agents.booking_agent import BookingAgent
from ..core.cta_engine import CTAEngine
from ..core.conversation_memory import ConversationMemory
from ..core.error_handling import ErrorHandler, ValidationError, AgentError, LLMError

from ..llm.rate_limited_client import RateLimitedLLMClient
from ..services.email_service import EmailService


class WorkflowState(TypedDict):
    """State for the LangGraph workflow"""
    # Input
    message: str
    platform: str
    device: str
    language: str
    conversationId: Optional[str]
    
    # Processing
    platform_context: Optional[PlatformContext]
    intent: Optional[str]
    response: Optional[Dict[str, Any]]
    
    # Language enrichment
    language_enriched: Optional[bool]
    
    # Output
    final_response: Optional[ChatResponse]
    error: Optional[str]


class AIAgentOrchestrator:
    """AI Agent Orchestrator - LangGraph-based workflow for TripC.AI Chatbot"""
    
    def __init__(self, qna_agent: QnAAgent, service_agent: ServiceAgent, llm_client: RateLimitedLLMClient = None, email_service: Optional[EmailService] = None):
        self.qna_agent = qna_agent
        self.service_agent = service_agent
        
        # Create rate-limited LLM client if not provided
        if llm_client is None:
            from ..llm.open_client import OpenAIClient
            base_llm_client = OpenAIClient()
            self.llm_client = RateLimitedLLMClient(base_llm_client)
        else:
            self.llm_client = llm_client
            
        self.cta_engine = CTAEngine()
        self.memory = ConversationMemory()
        self.booking_agent = BookingAgent(self.memory, email_service, self.llm_client, service_agent)

        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create the workflow
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("validate_platform", self._validate_platform)
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("rewrite_to_standalone", self._rewrite_to_standalone)
        workflow.add_node("route_to_agent", self._route_to_agent)
        workflow.add_node("add_cta", self._add_cta)
        workflow.add_node("enrich_language", self._enrich_language)
        workflow.add_node("format_response", self._format_response)
        
        # Add edges
        workflow.set_entry_point("validate_platform")
        workflow.add_edge("validate_platform", "classify_intent")
        workflow.add_edge("classify_intent", "rewrite_to_standalone")
        workflow.add_edge("rewrite_to_standalone", "route_to_agent")
        workflow.add_edge("route_to_agent", "add_cta")
        workflow.add_edge("add_cta", "enrich_language")
        workflow.add_edge("enrich_language", "format_response")
        workflow.add_edge("format_response", END)
        
        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "validate_platform",
            self._should_continue,
            {
                "continue": "classify_intent",
                "error": END
            }
        )
        
        # Add conditional edges for rewrite_to_standalone clarification handling
        workflow.add_conditional_edges(
            "rewrite_to_standalone",
            self._should_continue_after_rewrite,
            {
                "continue": "route_to_agent",
                "clarify": "add_cta"  # Skip routing, go directly to CTA
            }
        )
        
        return workflow.compile()
    
    async def _validate_platform(self, state: WorkflowState) -> WorkflowState:
        """Validate platform-device compatibility"""
        try:
            platform = PlatformType(state["platform"])
            device = DeviceType(state["device"])
            language = LanguageType(state["language"])
            
            # Validate platform-device compatibility
            if platform == PlatformType.MOBILE_APP and device == DeviceType.DESKTOP:
                raise ValidationError("Mobile app platform cannot be used with desktop device")
            
            # Create platform context
            platform_context = PlatformContext(
                platform=platform,
                device=device,
                language=language
            )
            
            state["platform_context"] = platform_context
            return state
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Platform validation error: {str(e)}")
    
    def _should_continue(self, state: WorkflowState) -> str:
        """Determine if workflow should continue or end with error"""
        if state.get("error"):
            return "error"
        return "continue"
    
    def _should_continue_after_rewrite(self, state: WorkflowState) -> str:
        """Determine if workflow should continue to routing or skip to CTA for clarification"""
        if state.get("needs_clarification"):
            return "clarify"
        return "continue"
    
    async def _classify_intent(self, state: WorkflowState) -> WorkflowState:
        """Classify user intent using LLM for intelligent classification with deep reasoning"""
        try:
            message = state["message"]
            language = state.get("language", "vi")
            conversation_id = state.get("conversationId") or "default"
            
            # Extract user identifier from conversation_id if available
            user_identifier = None
            if conversation_id and conversation_id != "default":
                # Try to extract user identifier from conversation_id format: user_xxx_timestamp_random
                parts = conversation_id.split("_")
                if len(parts) >= 2 and parts[0] in ["user", "session"]:
                    user_identifier = f"{parts[0]}_{parts[1]}"
            
            # Get conversation history and context for deep reasoning
            recent_turns = self.memory.get_recent(conversation_id, k=6)  # Get more context
            entities = self.memory.get_entities(conversation_id)
            
            # Build context information
            context_info = self._build_context_for_intent(recent_turns, entities, language)
            
            print(f"🤔 [INTENT ANALYSIS] Analyzing message: '{message}'")
            print(f"📚 [CONTEXT] Recent turns: {len(recent_turns)}, Entities: {list(entities.keys()) if entities else 'None'}")
            
            # Enhanced LLM-based intent classification with deep reasoning
            if self.llm_client and self.llm_client.is_configured():
                try:
                    intent_result = await self._llm_deep_intent_classification(
                        message, context_info, language
                    )
                    
                    if intent_result.get("confidence") == "high":
                        state["intent"] = intent_result["intent"]
                        print(f"✅ [INTENT] High confidence: {intent_result['intent']} - {intent_result['reasoning']}")
                    elif intent_result.get("confidence") == "medium":
                        state["intent"] = intent_result["intent"]
                        print(f"⚠️ [INTENT] Medium confidence: {intent_result['intent']} - {intent_result['reasoning']}")
                    else:
                        # Low confidence - ask for clarification
                        state["needs_clarification"] = True
                        state["clarify_question"] = intent_result.get("clarification_question", "")
                        state["intent"] = "qna"  # Default to qna while clarifying
                        print(f"❓ [INTENT] Low confidence - asking: {intent_result.get('clarification_question', '')}")
                        
                except Exception as e:
                    print(f"❌ [INTENT] LLM classification failed: {e}, falling back to keywords")
                    state["intent"] = self._fallback_keyword_classification(message)
            else:
                # Fallback to keyword-based classification if no LLM client
                state["intent"] = self._fallback_keyword_classification(message)
                print(f"🔍 [INTENT] Using keyword fallback: {state['intent']}")
            
            return state
            
        except Exception as e:
            print(f"❌ [INTENT] Intent classification error: {e}")
            state["intent"] = "qna"
            return state

    def _build_context_for_intent(self, recent_turns: list, entities: dict, language: str) -> dict:
        """Build comprehensive context for intent classification"""
        context = {
            "recent_conversation": [],
            "current_topics": [],
            "user_preferences": {},
            "booking_state": None,
            "mentioned_places": [],
            "conversation_flow": "new"
        }
        
        # Extract recent conversation flow
        for turn in recent_turns[-4:]:  # Last 4 turns
            if turn.get("role") and turn.get("content"):
                context["recent_conversation"].append({
                    "role": turn["role"],
                    "content": turn["content"][:100] + "..." if len(turn["content"]) > 100 else turn["content"]
                })
        
        # Extract current topics and preferences
        if entities:
            context["current_topics"] = [
                entities.get("current_place"),
                entities.get("last_mentioned_place"),
                entities.get("current_topic"),
                entities.get("last_subject")
            ]
            context["current_topics"] = [t for t in context["current_topics"] if t]
            
            # Extract user preferences
            context["user_preferences"] = {
                "name": entities.get("user_name"),
                "email": entities.get("user_email"),
                "phone": entities.get("user_phone"),
                "language": entities.get("user_language")
            }
            
            # Check booking state
            booking = entities.get("booking")
            if booking and isinstance(booking, dict):
                context["booking_state"] = {
                    "status": booking.get("status"),
                    "restaurant": booking.get("restaurant"),
                    "party_size": booking.get("party_size"),
                    "time": booking.get("time")
                }
        
        # Determine conversation flow
        if len(recent_turns) > 2:
            context["conversation_flow"] = "ongoing"
        else:
            context["conversation_flow"] = "new"
        
        return context

    async def _llm_deep_intent_classification(self, message: str, context: dict, language: str) -> dict:
        """Deep intent classification using LLM with context and reasoning"""
        
        if language == "vi":
            system_prompt = """Bạn là chuyên gia phân tích ý định người dùng với khả năng suy luận sâu.

NHIỆM VỤ: Phân tích câu hỏi của người dùng và xác định ý định chính xác nhất.

3 LOẠI Ý ĐỊNH:
1. service: Người dùng muốn TÌM/KHÁM PHÁ/ĐỀ XUẤT dịch vụ để sử dụng
   - Tìm nhà hàng, khách sạn, tour, địa điểm
   - Khám phá ẩm thực, văn hóa, điểm đến
   - Đề xuất nơi ăn, nơi nghỉ, nơi tham quan

2. booking: Người dùng có Ý ĐỊNH ĐẶT CHỖ/GIAO DỊCH
   - Đặt bàn, đặt phòng, đặt tour
   - Xác nhận giữ chỗ, thanh toán
   - Yêu cầu liên hệ để đặt

3. qna: Người dùng HỎI THÔNG TIN/TƯ VẤN
   - Thông tin mô tả, đánh giá, so sánh
   - Giá vé, giờ mở cửa, chính sách
   - Tư vấn, gợi ý, khuyên bảo

QUY TẮC SUY LUẬN:
- Phân tích ngữ cảnh cuộc hội thoại gần đây
- Xem xét trạng thái booking hiện tại
- Hiểu ý định ẩn trong câu hỏi
- Nếu chưa chắc chắn, hỏi lại để làm rõ

TRẢ VỀ JSON:
{
  "intent": "service|booking|qna",
  "confidence": "high|medium|low",
  "reasoning": "lý do chi tiết",
  "clarification_question": "câu hỏi làm rõ (nếu confidence=low)"
}"""
            
            user_prompt = f"""NGỮ CẢNH HỘI THOẠI:
{self._format_context_for_prompt(context, language)}

CÂU HỎI HIỆN TẠI: "{message}"

Hãy phân tích và trả về JSON."""
            
        else:
            system_prompt = """You are an expert user intent analyzer with deep reasoning capabilities.

TASK: Analyze the user's question and determine the most accurate intent.

3 INTENT TYPES:
1. service: User wants to FIND/EXPLORE/RECOMMEND services to use
   - Find restaurants, hotels, tours, destinations
   - Explore cuisine, culture, attractions
   - Suggest places to eat, stay, visit

2. booking: User INTENDS to BOOK/MAKE TRANSACTION
   - Book table, room, tour
   - Confirm reservation, payment
   - Request contact for booking

3. qna: User ASKS for INFORMATION/ADVICE
   - Description, reviews, comparisons
   - Ticket prices, opening hours, policies
   - Advice, suggestions, recommendations

REASONING RULES:
- Analyze recent conversation context
- Consider current booking state
- Understand hidden intent in questions
- If uncertain, ask for clarification

RETURN JSON:
{
  "intent": "service|booking|qna",
  "confidence": "high|medium|low",
  "reasoning": "detailed reasoning",
  "clarification_question": "clarification question (if confidence=low)"
}"""
            
            user_prompt = f"""CONVERSATION CONTEXT:
{self._format_context_for_prompt(context, language)}

CURRENT QUESTION: "{message}"

Please analyze and return JSON."""
        
        combined_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
        
        try:
            llm_response = self.llm_client.generate_response_sync(
                prompt=combined_prompt,
                max_tokens=300,
                temperature=0.1
            )
            
            if llm_response:
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    
                    # Validate intent
                    intent = data.get("intent", "").lower()
                    if intent not in ["service", "booking", "qna"]:
                        intent = "qna"  # Default fallback
                    
                    confidence = data.get("confidence", "low").lower()
                    reasoning = data.get("reasoning", "")
                    clarification_question = data.get("clarification_question", "")
                    
                    return {
                        "intent": intent,
                        "confidence": confidence,
                        "reasoning": reasoning,
                        "clarification_question": clarification_question
                    }
            
            # Fallback if JSON parsing fails
            return {
                "intent": "qna",
                "confidence": "low",
                "reasoning": "JSON parsing failed",
                "clarification_question": "Bạn có thể nói rõ hơn về điều bạn muốn hỏi không?"
            }
            
        except Exception as e:
            print(f"❌ [INTENT] LLM deep classification error: {e}")
            return {
                "intent": "qna",
                "confidence": "low",
                "reasoning": f"LLM error: {str(e)}",
                "clarification_question": "Bạn có thể nói rõ hơn về điều bạn muốn hỏi không?"
            }

    def _format_context_for_prompt(self, context: dict, language: str) -> str:
        """Format context information for LLM prompt"""
        if language == "vi":
            formatted = []
            
            # Recent conversation
            if context["recent_conversation"]:
                formatted.append("HỘI THOẠI GẦN ĐÂY:")
                for turn in context["recent_conversation"]:
                    role = "Người dùng" if turn["role"] == "user" else "Bot"
                    formatted.append(f"- {role}: {turn['content']}")
            
            # Current topics
            if context["current_topics"]:
                formatted.append(f"CHỦ ĐỀ HIỆN TẠI: {', '.join(context['current_topics'])}")
            
            # Booking state
            if context["booking_state"]:
                booking = context["booking_state"]
                formatted.append(f"TRẠNG THÁI ĐẶT CHỖ: {booking['status']}")
                if booking.get("restaurant"):
                    formatted.append(f"- Nhà hàng: {booking['restaurant']}")
                if booking.get("party_size"):
                    formatted.append(f"- Số người: {booking['party_size']}")
                if booking.get("time"):
                    formatted.append(f"- Thời gian: {booking['time']}")
            
            # User preferences
            if context["user_preferences"].get("name"):
                formatted.append(f"TÊN NGƯỜI DÙNG: {context['user_preferences']['name']}")
            
            # Conversation flow
            formatted.append(f"LOẠI HỘI THOẠI: {context['conversation_flow']}")
            
        else:
            formatted = []
            
            # Recent conversation
            if context["recent_conversation"]:
                formatted.append("RECENT CONVERSATION:")
                for turn in context["recent_conversation"]:
                    role = "User" if turn["role"] == "user" else "Bot"
                    formatted.append(f"- {role}: {turn['content']}")
            
            # Current topics
            if context["current_topics"]:
                formatted.append(f"CURRENT TOPICS: {', '.join(context['current_topics'])}")
            
            # Booking state
            if context["booking_state"]:
                booking = context["booking_state"]
                formatted.append(f"BOOKING STATE: {booking['status']}")
                if booking.get("restaurant"):
                    formatted.append(f"- Restaurant: {booking['restaurant']}")
                if booking.get("party_size"):
                    formatted.append(f"- Party size: {booking['party_size']}")
                if booking.get("time"):
                    formatted.append(f"- Time: {booking['time']}")
            
            # User preferences
            if context["user_preferences"].get("name"):
                formatted.append(f"USER NAME: {context['user_preferences']['name']}")
            
            # Conversation flow
            formatted.append(f"CONVERSATION TYPE: {context['conversation_flow']}")
        
        return "\n".join(formatted)

    def _user_wants_to_continue_booking(self, message: str, original_intent: str) -> bool:
        """Check if user wants to continue booking or do something else"""
        message_lower = message.lower().strip()
        
        # If original intent is already booking, user likely wants to continue
        if original_intent == "booking":
            return True
            
        # Keywords that indicate user wants to continue booking
        booking_continuation_keywords = [
            # Providing booking information
            "tên tôi là", "tên tôi", "my name is", "my name",
            "số điện thoại", "điện thoại", "phone", "sdt",
            "email", "mail", "e-mail",
            "địa chỉ", "address",
            
            # Confirming booking
            "xác nhận", "confirm", "đồng ý", "agree", "ok", "okay",
            "chốt", "gửi", "send", "hoàn tất", "finish", "done",
            
            # Booking details
            "số người", "mấy người", "how many people", "party size",
            "thời gian", "lúc", "giờ", "time", "when",
            "ngày", "date", "hôm nay", "today", "tối nay", "tonight",
            
            # Direct booking actions
            "đặt bàn", "book table", "đặt chỗ", "reserve",
            "đặt phòng", "book room", "đặt tour", "book tour"
        ]
        
        # Keywords that indicate user wants to do something else
        other_action_keywords = [
            # Service discovery
            "gợi ý", "suggest", "tìm", "find", "search", "khám phá", "explore",
            "nhà hàng khác", "other restaurants", "thêm", "more",
            "xem", "show", "danh sách", "list",
            
            # Information requests
            "là gì", "what is", "tại sao", "why", "như thế nào", "how",
            "giá", "price", "cost", "đẹp không", "is it beautiful",
            "giờ mở cửa", "opening hours", "địa chỉ", "address",
            
            # General questions
            "có gì", "what's", "thông tin", "information", "mô tả", "description",
            "đánh giá", "review", "rating", "feedback"
        ]
        
        # Check for booking continuation keywords
        has_booking_keywords = any(keyword in message_lower for keyword in booking_continuation_keywords)
        
        # Check for other action keywords
        has_other_keywords = any(keyword in message_lower for keyword in other_action_keywords)
        
        # Decision logic
        if has_booking_keywords and not has_other_keywords:
            return True  # User wants to continue booking
        elif has_other_keywords and not has_booking_keywords:
            return False  # User wants to do something else
        elif has_booking_keywords and has_other_keywords:
            # Mixed signals - use LLM to decide
            return self._llm_decide_booking_continuation(message)
        else:
            # No clear keywords - default to continue booking if in booking flow
            return True
    
    def _llm_decide_booking_continuation(self, message: str) -> bool:
        """Use LLM to decide if user wants to continue booking when signals are mixed"""
        try:
            if not self.llm_client or not self.llm_client.is_configured():
                return True  # Default to continue booking if LLM not available
            
            prompt = f"""Phân tích câu hỏi của người dùng và xác định họ có muốn tiếp tục quá trình đặt bàn hay không.

Câu hỏi: "{message}"

Trả về JSON:
{{"continue_booking": true/false, "reason": "lý do"}}

- continue_booking = true: Người dùng muốn tiếp tục đặt bàn (cung cấp thông tin, xác nhận, hoàn tất)
- continue_booking = false: Người dùng muốn làm việc khác (tìm kiếm, hỏi thông tin, gợi ý)

Chỉ trả về JSON, không có text khác."""
            
            response = self.llm_client.generate_response_sync(prompt, max_tokens=100, temperature=0.1)
            
            if response:
                import json
                import re
                
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    return data.get("continue_booking", True)
            
            return True  # Default to continue booking
            
        except Exception as e:
            print(f"⚠️ [LLM DECISION] Error in booking continuation decision: {e}")
            return True  # Default to continue booking
    
    async def _rewrite_to_standalone(self, state: WorkflowState) -> WorkflowState:
        """Rewrite current message to a standalone question using recent context"""
        try:
            conversation_id = state.get("conversationId") or "default"
            recent_turns = self.memory.get_recent(conversation_id, k=4)
            entities = self.memory.get_entities(conversation_id)
            message = state["message"]
            language = state.get("language", "vi")

            # Heuristic pronoun resolution
            def heuristic_fill(msg: str) -> Optional[str]:
                lower = msg.lower()
                pronouns_vi = ["ở đó", "nó", "chỗ đó", "nơi đó", "đó", "đấy", "cái đó", "điều đó"]
                pronouns_en = ["there", "it", "that place", "that", "this"]
                pronouns = pronouns_vi + pronouns_en
                if any(p in lower for p in pronouns):
                    # Infer subject from memory or recent user turns
                    subject = (
                        entities.get("current_place")
                        or entities.get("last_mentioned_place")
                        or entities.get("current_topic")
                        or entities.get("last_subject")
                    )
                    if not subject:
                        # find last user message
                        for turn in reversed(recent_turns):
                            if turn.get("role") == "user":
                                cand = turn.get("content")
                                if cand and cand.strip() and cand.strip() != msg.strip():
                                    subject = cand.strip()
                                    break
                    if subject:
                        filled = msg
                        for p in pronouns_vi:
                            filled = filled.replace(p, subject)
                        for p in pronouns_en:
                            filled = filled.replace(p, subject)
                        return filled
                return None

            rewritten = heuristic_fill(message)

            # LLM-based pronoun resolution and clarification if still ambiguous
            if not rewritten and self.llm_client and self.llm_client.is_configured():
                history_text = "\n".join([f"{t['role']}: {t['content']}" for t in recent_turns])
                subjects = {
                    "current_place": entities.get("current_place"),
                    "last_mentioned_place": entities.get("last_mentioned_place"),
                    "current_topic": entities.get("current_topic"),
                    "last_subject": entities.get("last_subject"),
                }
                if language == "vi":
                    system = (
                        "Bạn là trợ lý suy luận ngữ cảnh. NHIỆM VỤ: nếu câu của người dùng dùng đại từ mơ hồ "
                        "(ví dụ: 'ở đó', 'cái đó', 'nó', 'đó') thì hãy QUYẾT ĐỊNH:\n"
                        "- Nếu xác định được chủ thể từ ngữ cảnh, trả về JSON: {\"action\":\"rewrite\", \"rewritten\": \"...\"}\n"
                        "- Nếu KHÔNG chắc chắn, trả về JSON: {\"action\":\"clarify\", \"question\": \"Câu hỏi làm rõ ngắn gọn\"}\n"
                        "KHÔNG trả lời tự do, CHỈ JSON."
                    )
                    user = (
                        f"Ngữ cảnh:\n{history_text}\n\n"
                        f"Chủ thể gợi ý: {subjects}\n\n"
                        f"Câu người dùng: {message}\n"
                        "Trả về JSON."
                    )
                else:
                    system = (
                        "You are a context reasoner. If the user message uses ambiguous pronouns "
                        "(e.g., 'there', 'it', 'that'), DECIDE:\n"
                        "- If you can infer the subject from context, return JSON: {\"action\":\"rewrite\", \"rewritten\": \"...\"}\n"
                        "- If NOT confident, return JSON: {\"action\":\"clarify\", \"question\": \"Short clarification question\"}\n"
                        "Return JSON ONLY."
                    )
                    user = (
                        f"Context:\n{history_text}\n\n"
                        f"Subject hints: {subjects}\n\n"
                        f"User message: {message}\n"
                        "Return JSON."
                    )
                prompt = f"System: {system}\n\nUser: {user}"
                out = self.llm_client.generate_response_sync(prompt, max_tokens=160, temperature=0.1)
                if out:
                    try:
                        import json, re
                        m = re.search(r"\{[\s\S]*\}", out)
                        if m:
                            data = json.loads(m.group(0))
                            action = (data.get("action") or "").lower()
                            if action == "rewrite" and data.get("rewritten"):
                                rewritten = str(data["rewritten"]).strip()
                            elif action == "clarify" and data.get("question"):
                                # Ask clarification in next node
                                state["needs_clarification"] = True
                                state["clarify_question"] = str(data["question"]).strip()
                    except Exception:
                        pass

            state["message"] = rewritten or message
            # Persist resolved subject for next turns if we changed the message
            if rewritten and rewritten != message:
                try:
                    # Save a lightweight subject for future references
                    subject_hint = rewritten
                    self.memory.update_entities_safe(conversation_id, {
                        "last_subject": subject_hint,
                        "current_topic": subject_hint
                    }, "rewrite_to_standalone")
                except Exception:
                    pass
            return state
        except Exception as e:
            print(f"❌ Rewrite error: {e}")
            return state
    
    def _fallback_keyword_classification(self, message: str) -> str:
        """Fallback keyword-based intent classification when LLM is unavailable"""
        message_lower = message.lower()
        
        # Service intent keywords - tìm kiếm, khám phá, xem danh sách, nhu cầu sử dụng dịch vụ
        service_keywords = [
            # Từ khóa tìm kiếm
            "tìm", "search", "find", "khám phá", "explore", "discover",
            "xem", "show", "danh sách", "list", 
            # Địa điểm cụ thể (chỉ khi tìm kiếm)
            "nhà hàng", "restaurant", "quán ăn", "food", "dining",
            "khách sạn", "hotel", "resort", "accommodation",
            "tour", "sightseeing", "tham quan",
            # Từ khóa vị trí
            "ở đâu", "where", "địa chỉ", "address", "gần đây", "nearby",
            "xung quanh", "around", "khu vực", "area", "đường", "street",
            # Nhu cầu sử dụng dịch vụ
            "ăn uống", "ăn", "bữa", "ngủ", "nghỉ ngơi", "thư giãn", "rest", "relax"
        ]
        
        # Booking intent keywords - đặt chỗ, giao dịch
        booking_keywords = [
            # Từ khóa đặt chỗ
            "đặt", "book", "reserve", "booking", "reservation",
            "đặt bàn", "book table", "đặt chỗ", "book seat",
            "đặt tour", "book tour", "đặt vé", "book ticket",
            "đặt phòng", "book room", "đặt khách sạn", "book hotel",
            # Từ khóa giao dịch
            "thanh toán", "payment", "pay", "mua", "buy", "purchase",
            "giá", "price", "cost", "chi phí", "fee", "phí",
            # Từ khóa xác nhận
            "xác nhận", "confirm", "đồng ý", "agree", "ok", "okay"
        ]
        
        # QnA intent keywords - câu hỏi, tư vấn, thông tin chung
        qna_keywords = [
            # Câu hỏi
            "là gì", "what is", "tại sao", "why", "như thế nào", "how",
            "bao giờ", "when", "ai", "who", "cái gì", "what",
            # Từ khóa tư vấn
            "tư vấn", "advice", "gợi ý", "suggest", "khuyên", "recommend",
            "nên", "should", "có nên", "is it good", "có tốt không",
            # Từ khóa thông tin chung
            "xin chào", "hello", "hi", "chào", "greeting",
            "giờ mở cửa", "opening hours", "giờ đóng cửa", "closing time",
            "chính sách", "policy", "điều kiện", "condition", "quy định", "rule",
            # Thông tin/đánh giá/vé
            "đẹp không", "review", "đánh giá", "giá vé", "vé bao nhiêu", "ticket", "ticket price"
        ]
        
        # Check for QnA intent first (câu hỏi thông tin có priority cao)
        qna_indicators = [
            "giới thiệu về", "introduce about", "thông tin về", "info about",
            "có gì", "what is", "là gì", "what's", "như thế nào", "how is",
            "bảo tàng", "museum", "di tích", "heritage", "di sản", "heritage site",
            "đẹp không", "giá vé", "ticket price", "opening hours"
        ]
        
        if any(indicator in message_lower for indicator in qna_indicators):
            return "qna"
        
        # Check for booking intent (second priority)
        if any(keyword in message_lower for keyword in booking_keywords):
            return "booking"
        # Check for service intent
        elif any(keyword in message_lower for keyword in service_keywords):
            return "service"
        # Check for QnA intent
        elif any(keyword in message_lower for keyword in qna_keywords):
            return "qna"
        else:
            # Default to QnA for unclear intent
            return "qna"
    
    async def _route_to_agent(self, state: WorkflowState) -> WorkflowState:
        """Route request to appropriate agent with enhanced logging and clarification handling"""
        intent = state["intent"]
        original_intent = intent
        platform_context = state["platform_context"]
        message = state["message"]
        conversation_id = state.get("conversationId") or "default"
        
        print(f"🔄 [ROUTING] Routing to agent: {intent}")
        print(f"📝 [MESSAGE] User message: '{message}'")
        
        try:
            # Smart booking flow routing: check if user wants to continue booking or do something else
            try:
                entities = self.memory.get_entities(conversation_id)
                booking_state = entities.get("booking") if isinstance(entities, dict) else None
                if booking_state and isinstance(booking_state, dict):
                    status = booking_state.get("status")
                    if status in ("collecting", "ready"):
                        # Check if user wants to continue booking or do something else
                        if self._user_wants_to_continue_booking(message, original_intent):
                            original_intent = intent
                            intent = "booking"
                            print(f"📋 [BOOKING FLOW] User wants to continue booking - overriding intent from {original_intent} to booking (status: {status})")
                        else:
                            print(f"🔄 [BOOKING FLOW] User wants to do something else - keeping intent as {intent} (status: {status})")
            except Exception as e:
                print(f"⚠️ [ROUTING] Error checking booking state: {e}")

            # Route based on intent
            if intent == "service":
                print(f"🏪 [SERVICE AGENT] Routing to service agent")
                # Route to service agent
                response = await self.service_agent.get_services(
                    query=message,
                    platform_context=platform_context,
                    service_type="restaurant"
                )
                state["response"] = response.dict()
                print(f"✅ [SERVICE AGENT] Response generated successfully")
                
                # Store entity for follow-ups
                try:
                    services = state["response"].get("services") or []
                    if services:
                        top = services[0]
                        place_name = top.get("name")
                        if place_name:
                            self.memory.update_entities_safe(conversation_id, {
                                "current_place": place_name,
                                "last_mentioned_place": place_name
                            }, "service_agent")
                            print(f"💾 [MEMORY] Stored place: {place_name}")
                except Exception as e:
                    print(f"⚠️ [MEMORY] Error storing service entities: {e}")
                
            elif intent == "booking":
                print(f"📅 [BOOKING AGENT] Routing to booking agent")
                # Conversational booking flow via BookingAgent
                booking_response = await self.booking_agent.handle(
                    conversation_id=conversation_id,
                    message=message,
                    platform_context=platform_context,
                )
                state["response"] = booking_response.dict()
                print(f"✅ [BOOKING AGENT] Response generated successfully")
                
            else:
                print(f"❓ [QNA AGENT] Routing to QnA agent")
                # Route to QnA agent
                response = await self.qna_agent.search_embedding(
                    query=message,
                    platform_context=platform_context
                )
                state["response"] = response.dict()
                print(f"✅ [QNA AGENT] Response generated successfully")
                
                # Store topic/subject to help resolve follow-ups like "ở đó/cái đó"
                try:
                    sources = state["response"].get("sources") or []
                    top_title = sources[0].get("title") if sources else None
                    subject = top_title or message
                    self.memory.update_entities_safe(conversation_id, {
                        "last_subject": subject,
                        "current_topic": subject
                    }, "qna_agent")
                    print(f"💾 [MEMORY] Stored subject: {subject}")
                except Exception as e:
                    print(f"⚠️ [MEMORY] Error storing QnA entities: {e}")
            
            return state
            
        except Exception as e:
            print(f"❌ [ROUTING] Agent routing error: {e}")
            raise AgentError(f"Agent routing error: {str(e)}", "orchestrator")
    
    async def _add_cta(self, state: WorkflowState) -> WorkflowState:
        """Add platform-specific CTA to response with enhanced clarification handling"""
        if state.get("error"):
            return state
        
        platform_context = state["platform_context"]
        
        # Handle clarification case - create response here
        if state.get("needs_clarification"):
            ask = state.get("clarify_question") or (
                "Bạn đang nói đến địa điểm hay nội dung nào ạ?" if platform_context.language.value == "vi"
                else "Which place or topic do you mean?"
            )
            
            print(f"❓ [CLARIFICATION] Asking for clarification: '{ask}'")
            
            ask_response = QnAResponse(
                type="QnA",
                answerAI=ask,
                sources=[],
                suggestions=[
                    Suggestion(
                        label=("Mô tả rõ" if platform_context.language.value == "vi" else "Specify"), 
                        action="clarify_subject"
                    ),
                    Suggestion(
                        label=("Tìm nhà hàng" if platform_context.language.value == "vi" else "Find restaurants"), 
                        action="search_services"
                    ),
                    Suggestion(
                        label=("Đặt bàn" if platform_context.language.value == "vi" else "Book table"), 
                        action="start_booking"
                    )
                ]
            )
            state["response"] = ask_response.dict()
            # Clear one-shot clarification flags
            state.pop("needs_clarification", None)
            state.pop("clarify_question", None)
            print(f"✅ [CLARIFICATION] Clarification response created")
        
        response = state["response"]
        
        try:
            # Generate CTA based on platform and response type
            if response.get("type") == "Service" and response.get("services"):
                # Get first service for CTA
                first_service = response["services"][0] if response["services"] else None
                service_id = first_service["id"] if first_service else None
                service_type = first_service["type"] if first_service else "restaurant"
                
                cta = self.cta_engine.generate_platform_cta(
                    platform=platform_context.platform,
                    device=platform_context.device,
                    service_id=service_id,
                    service_type=service_type
                )
            else:
                # General CTA
                cta = self.cta_engine.generate_platform_cta(
                    platform=platform_context.platform,
                    device=platform_context.device
                )
            
            # Convert CTA to dict, excluding None values
            cta_dict = cta.dict()
            if cta_dict.get("deeplink") is None:
                cta_dict.pop("deeplink", None)
            if cta_dict.get("url") is None:
                cta_dict.pop("url", None)
            response["cta"] = cta_dict
            state["response"] = response
            
            return state
            
        except Exception as e:
            raise AgentError(f"CTA generation error: {str(e)}", "cta_engine")
    
    async def _enrich_language(self, state: WorkflowState) -> WorkflowState:
        """Enrich answerAI language using LLM for booking and service responses only"""
        try:
            response = state["response"]
            response_type = response.get("type", "")
            answer_ai = response.get("answerAI", "")
            language = state.get("language", "vi")
            
            # Only enrich for booking and service responses, not QnA embedding
            # QnA from booking agent can still be enriched
            if response_type in ["Service", "booking", "QnA"] and answer_ai and self.llm_client and self.llm_client.is_configured():
                # Skip enrichment for QnA embedding responses (from QnAAgent)
                # But allow enrichment for QnA from booking agent
                if response_type == "QnA":
                    # Check if this is from QnAAgent (embedding-based) or booking agent
                    # We can detect this by checking if there are sources (embedding-based QnA has sources)
                    sources = response.get("sources", [])
                    if sources:
                        print(f"⏭️ [LANGUAGE ENRICHMENT] Skipping QnA embedding response (has sources)")
                        state["response"] = response
                        return state
                    else:
                        print(f"🎨 [LANGUAGE ENRICHMENT] Enriching QnA from booking agent")
                else:
                    print(f"🎨 [LANGUAGE ENRICHMENT] Enriching {response_type} response")
                
                try:
                    enriched_answer = await self._llm_enrich_language(answer_ai, response_type, language)
                    if enriched_answer and enriched_answer.strip():
                        response["answerAI"] = enriched_answer
                        state["language_enriched"] = True
                        print(f"✅ [LANGUAGE ENRICHMENT] Successfully enriched response")
                    else:
                        print(f"⚠️ [LANGUAGE ENRICHMENT] No enrichment applied, keeping original")
                except Exception as e:
                    print(f"⚠️ [LANGUAGE ENRICHMENT] Error enriching language: {e}, keeping original")
            else:
                print(f"⏭️ [LANGUAGE ENRICHMENT] Skipping enrichment for {response_type} response")
            
            state["response"] = response
            return state
            
        except Exception as e:
            print(f"❌ [LANGUAGE ENRICHMENT] Error in language enrichment: {e}")
            return state
    
    async def _llm_enrich_language(self, original_answer: str, response_type: str, language: str) -> str:
        """Use LLM to enrich language naturally without changing core meaning"""
        
        if language == "vi":
            system_prompt = """Bạn là chuyên gia làm giàu ngôn ngữ tự nhiên. NHIỆM VỤ: Làm giàu câu trả lời để tự nhiên hơn, thân thiện hơn nhưng KHÔNG thay đổi ý nghĩa cốt lõi.

QUY TẮC:
1. GIỮ NGUYÊN ý nghĩa chính và thông tin quan trọng
2. Thêm từ ngữ tự nhiên, thân thiện, ấm áp
3. Sử dụng ngôn ngữ giao tiếp tự nhiên
4. KHÔNG thêm thông tin mới không có trong câu gốc
5. KHÔNG thay đổi cấu trúc logic

VÍ DỤ:
- Gốc: "Tìm thấy 5 nhà hàng"
- Làm giàu: "Tôi đã tìm thấy 5 nhà hàng tuyệt vời cho bạn"
- Gốc: "Đặt bàn thành công"
- Làm giàu: "Tuyệt vời! Việc đặt bàn của bạn đã được xác nhận thành công"

Chỉ trả về câu trả lời đã làm giàu, không có giải thích."""
            
            user_prompt = f"""Loại phản hồi: {response_type}
Câu trả lời gốc: "{original_answer}"

Hãy làm giàu ngôn ngữ một cách tự nhiên."""
            
        else:
            system_prompt = """You are a natural language enrichment expert. TASK: Enrich the response to make it more natural, friendly, and warm while NOT changing the core meaning.

RULES:
1. KEEP the main meaning and important information intact
2. Add natural, friendly, warm language
3. Use conversational, natural language
4. DO NOT add new information not in the original
5. DO NOT change the logical structure

EXAMPLES:
- Original: "Found 5 restaurants"
- Enriched: "I found 5 wonderful restaurants for you"
- Original: "Booking successful"
- Enriched: "Great! Your booking has been successfully confirmed"

Return only the enriched response, no explanations."""
            
            user_prompt = f"""Response type: {response_type}
Original response: "{original_answer}"

Please enrich the language naturally."""
        
        try:
            combined_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
            
            enriched = self.llm_client.generate_response_sync(
                prompt=combined_prompt,
                max_tokens=200,
                temperature=0.3  # Low temperature for consistency
            )
            
            if enriched and enriched.strip():
                # Clean up the response
                enriched = enriched.strip()
                # Remove quotes if present
                if enriched.startswith('"') and enriched.endswith('"'):
                    enriched = enriched[1:-1]
                if enriched.startswith("'") and enriched.endswith("'"):
                    enriched = enriched[1:-1]
                
                return enriched
            
            return original_answer
            
        except Exception as e:
            print(f"❌ [LLM ENRICHMENT] Error: {e}")
            return original_answer
    
    async def _format_response(self, state: WorkflowState) -> WorkflowState:
        """Format final response"""
        # Convert response to ChatResponse
        response_data = state["response"]
        
        # Map response type to ChatResponse
        if response_data.get("type") == "Service":
            final_response = ChatResponse(
                type="Service",
                answerAI=response_data.get("answerAI", ""),
                services=response_data.get("services", []),
                sources=response_data.get("sources", []),
                suggestions=response_data.get("suggestions", []),
                cta=response_data.get("cta")
            )
        else:
            final_response = ChatResponse(
                type="QnA",
                answerAI=response_data.get("answerAI", ""),
                sources=response_data.get("sources", []),
                suggestions=response_data.get("suggestions", []),
                cta=response_data.get("cta")
            )
        
        state["final_response"] = final_response
        
        return state
    
    async def process_request(self, request: ChatRequest) -> ChatResponse:
        """Process a chat request through the LangGraph workflow"""
        
        # Initialize state
        initial_state = WorkflowState(
            message=request.message,
            platform=request.platform,
            device=request.device,
            language=request.language,
            conversationId=getattr(request, "conversationId", None),
            platform_context=None,
            intent=None,
            response=None,
            language_enriched=False,
            final_response=None,
            error=None
        )
        
        # Execute workflow
        try:
            # Save user turn
            conversation_id = getattr(request, "conversationId", None) or "default"
            
            # Extract user identifier from conversation_id if available
            user_identifier = None
            if conversation_id and conversation_id != "default":
                parts = conversation_id.split("_")
                if len(parts) >= 2 and parts[0] in ["user", "session"]:
                    user_identifier = f"{parts[0]}_{parts[1]}"
            
            self.memory.add_turn(
                conversation_id, 
                "user", 
                request.message,
                meta={
                    "platform": request.platform,
                    "device": request.device, 
                    "language": request.language,
                    "user_identifier": user_identifier
                }
            )

            # Update persistent user entities (name/email/phone) from the latest message
            try:
                self._update_user_entities_from_message(conversation_id, request.message)
            except Exception:
                pass

            # Run the workflow
            result = await self.workflow.ainvoke(initial_state)
            
            # Return final response
            if result.get("final_response"):
                # Save assistant turn
                try:
                    self.memory.add_turn(conversation_id, "assistant", result["final_response"].answerAI, meta={"type": result["final_response"].type})
                except Exception:
                    pass
                return result["final_response"]
            else:
                # Fallback error response
                error_response = ErrorHandler.create_fallback_response(request.language)
                return ChatResponse(**error_response)
                
        except (ValidationError, AgentError, LLMError) as e:
            # Handle known workflow errors
            error_response = ErrorHandler.handle_workflow_error(e, request.language)
            return ChatResponse(**error_response)
        except Exception as e:
            # Handle unknown errors
            error_response = ErrorHandler.handle_generic_error(e, request.language)
            return ChatResponse(**error_response)
    
    def get_workflow_graph(self) -> Dict[str, Any]:
        """Get workflow graph for visualization"""
        return {
            "nodes": [
                {"id": "validate_platform", "type": "validation"},
                {"id": "classify_intent", "type": "classification"},
                {"id": "rewrite_to_standalone", "type": "rewriting"},
                {"id": "route_to_agent", "type": "routing"},
                {"id": "add_cta", "type": "enhancement"},
                {"id": "enrich_language", "type": "language_enrichment"},
                {"id": "format_response", "type": "formatting"}
            ],
            "edges": [
                {"from": "validate_platform", "to": "classify_intent"},
                {"from": "classify_intent", "to": "rewrite_to_standalone"},
                {"from": "rewrite_to_standalone", "to": "route_to_agent"},
                {"from": "route_to_agent", "to": "add_cta"},
                {"from": "add_cta", "to": "enrich_language"},
                {"from": "enrich_language", "to": "format_response"},
                {"from": "format_response", "to": "END"}
            ],
            "conditional_edges": [
                {
                    "from": "validate_platform",
                    "condition": "error",
                    "to": "END"
                },
                {
                    "from": "rewrite_to_standalone",
                    "condition": "clarify",
                    "to": "add_cta"
                }
            ]
        }

    def _update_user_entities_from_message(self, conversation_id: str, message: str) -> None:
        """Lightweight extraction of user-level entities and store to memory for reuse across flows."""
        text = message or ""
        entities_update: Dict[str, Any] = {}

        # Email
        m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", text)
        if m:
            entities_update["user_email"] = m.group(0)

        # Phone (basic)
        m = re.search(r"\+?\d{9,13}", text.replace(" ", ""))
        if m:
            entities_update["user_phone"] = m.group(0)

        # Name via label "Tên:" or statements "Tôi là/ I am / My name is"
        m = re.search(r"(tên|name)\s*:\s*([^,\n\r]{2,})", text, flags=re.IGNORECASE)
        if m:
            entities_update["user_name"] = m.group(2).strip()
        else:
            m = re.search(r"(tôi là|toi la|my name is|i am)\s+([^,\n\r]{2,})", text, flags=re.IGNORECASE)
            if m:
                entities_update["user_name"] = m.group(2).strip()

        if entities_update:
            self.memory.update_entities_safe(conversation_id, entities_update, "user_entity_extraction")