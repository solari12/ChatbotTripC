#!/usr/bin/env python3
"""
AI Agent Orchestrator - LangGraph-based workflow for TripC.AI Chatbot
Replaces the traditional orchestrator with a visual workflow
"""

from typing import Dict, Any, Optional, TypedDict
import re
from langgraph.graph import StateGraph, END

from ..models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType
from ..models.schemas import ChatRequest, ChatResponse, QnAResponse
from ..agents.qna_agent import QnAAgent
from ..agents.service_agent import ServiceAgent
from ..agents.booking_agent import BookingAgent
from ..core.cta_engine import CTAEngine
from ..core.conversation_memory import ConversationMemory

from ..llm.open_client import OpenAIClient
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
    
    # Output
    final_response: Optional[ChatResponse]
    error: Optional[str]


class AIAgentOrchestrator:
    """AI Agent Orchestrator - LangGraph-based workflow for TripC.AI Chatbot"""
    
    def __init__(self, qna_agent: QnAAgent, service_agent: ServiceAgent, llm_client: OpenAIClient = None, email_service: Optional[EmailService] = None):
        self.qna_agent = qna_agent
        self.service_agent = service_agent
        self.llm_client = llm_client or OpenAIClient()  # Auto-create if not provided
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
        workflow.add_node("route_to_agent", self._route_to_agent)
        workflow.add_node("rewrite_to_standalone", self._rewrite_to_standalone)
        workflow.add_node("add_cta", self._add_cta)
        workflow.add_node("format_response", self._format_response)
        
        # Add edges
        workflow.set_entry_point("validate_platform")
        workflow.add_edge("validate_platform", "classify_intent")
        workflow.add_edge("classify_intent", "rewrite_to_standalone")
        workflow.add_edge("rewrite_to_standalone", "route_to_agent")
        workflow.add_edge("route_to_agent", "add_cta")
        workflow.add_edge("add_cta", "format_response")
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
        
        return workflow.compile()
    
    async def _validate_platform(self, state: WorkflowState) -> WorkflowState:
        """Validate platform-device compatibility"""
        try:
            platform = PlatformType(state["platform"])
            device = DeviceType(state["device"])
            language = LanguageType(state["language"])
            
            # Validate platform-device compatibility
            if platform == PlatformType.MOBILE_APP and device == DeviceType.DESKTOP:
                state["error"] = "Mobile app platform cannot be used with desktop device"
                return state
            
            # Create platform context
            platform_context = PlatformContext(
                platform=platform,
                device=device,
                language=language
            )
            
            state["platform_context"] = platform_context
            return state
            
        except Exception as e:
            state["error"] = f"Platform validation error: {str(e)}"
            return state
    
    def _should_continue(self, state: WorkflowState) -> str:
        """Determine if workflow should continue or end with error"""
        if state.get("error"):
            return "error"
        return "continue"
    
    async def _classify_intent(self, state: WorkflowState) -> WorkflowState:
        """Classify user intent using LLM for intelligent classification"""
        try:
            message = state["message"]
            language = state.get("language", "vi")
            
            # Optimized prompts for fast and accurate intent classification
            if language == "vi":
                system_prompt = """Phân loại ý định người dùng (chỉ trả về đúng 1 từ: service/booking/qna):
- service: người dùng muốn TÌM/Khám phá/Đề xuất dịch vụ để sử dụng (ăn uống, nghỉ ngơi, khách sạn, nhà hàng, tour, điểm đến, kế hoạch đi đâu)
- booking: người dùng có Ý ĐỊNH ĐẶT chỗ/đặt bàn/đặt tour/xác nhận giữ chỗ/yêu cầu liên hệ để đặt
- qna: người dùng HỎI THÔNG TIN chung (mô tả, đánh giá, "đẹp không", giá vé, giờ mở cửa, so sánh, hướng dẫn)

Ví dụ:
- "Tôi muốn tìm nhà hàng hải sản" → service
- "Đặt bàn lúc 7h tối nay" → booking
- "Bảo tàng Đà Nẵng có đẹp không?" → qna

Chỉ trả về: service hoặc booking hoặc qna"""
                user_prompt = f"Câu: '{message}'\nKết quả:"
            else:
                system_prompt = """Classify intent (return exactly ONE word: service/booking/qna):
- service: user wants to FIND/Explore/Recommend services to use (food, rest, hotels, restaurants, tours, destinations, plan where to go)
- booking: user INTENDS to BOOK/reserve/confirm a table/tour or asks to be contacted to book
- qna: user ASKS general info (description, reviews, "is it beautiful?", ticket prices, opening hours, comparisons, guidance)

Examples:
- "Find a seafood restaurant" → service
- "Book a table at 7pm" → booking
- "Is Da Nang Museum beautiful?" → qna

Return only: service or booking or qna"""
                user_prompt = f"Input: '{message}'\nOutput:"
            
            # Use LLM to classify intent
            if self.llm_client:
                try:
                    # Get LLM response for intent classification
                    combined_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
                    llm_response = self.llm_client.generate_response(
                        prompt=combined_prompt,
                        model="gpt-3.5-turbo",  # Use appropriate model
                        max_tokens=5,  # Reduced for faster response
                        temperature=0.1  # Lower temperature for more consistent results
                    )
                    # Extract intent from LLM response - optimized parsing
                    intent_response = llm_response.strip().lower() if llm_response else ""
                    
                    # Fast intent mapping with exact matches
                    if intent_response in ["service", "s"]:
                        state["intent"] = "service"
                    elif intent_response in ["booking", "book", "b"]:
                        state["intent"] = "booking"
                    elif intent_response in ["qna", "q"]:
                        state["intent"] = "qna"
                    else:
                        # Fallback to qna if LLM response is unclear
                        state["intent"] = "qna"
                        
                except Exception as e:
                    # Fallback to keyword-based classification if LLM fails
                    print(f"❌ LLM intent classification failed: {e}, falling back to keywords")
                    state["intent"] = self._fallback_keyword_classification(message)
            else:
                # Fallback to keyword-based classification if no LLM client
                state["intent"] = self._fallback_keyword_classification(message)
            
            return state
            
        except Exception as e:
            # Error handling - default to qna
            print(f"❌ Intent classification error: {e}")
            state["intent"] = "qna"
            return state

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
                out = self.llm_client.generate_response(prompt, max_tokens=160, temperature=0.1)
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
                    self.memory.set_entities(conversation_id, {
                        "last_subject": subject_hint,
                        "current_topic": subject_hint
                    })
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
        """Route request to appropriate agent"""
        intent = state["intent"]
        platform_context = state["platform_context"]
        message = state["message"]
        conversation_id = state.get("conversationId") or "default"
        
        try:
            # If clarification is needed, ask user instead of proceeding
            if state.get("needs_clarification"):
                ask = state.get("clarify_question") or (
                    "Bạn đang nói đến địa điểm hay nội dung nào ạ?" if platform_context.language.value == "vi"
                    else "Which place or topic do you mean?"
                )
                ask_response = QnAResponse(
                    type="QnA",
                    answerAI=ask,
                    sources=[],
                    suggestions=[
                        {"label": ("Mô tả rõ" if platform_context.language.value == "vi" else "Specify"), "action": "clarify_subject"}
                    ]
                )
                state["response"] = ask_response.dict()
                # Clear one-shot clarification flags
                state.pop("needs_clarification", None)
                state.pop("clarify_question", None)
                return state

            # Persist booking flow across turns: if booking is in progress, keep routing to booking
            try:
                entities = self.memory.get_entities(conversation_id)
                booking_state = entities.get("booking") if isinstance(entities, dict) else None
                if booking_state and isinstance(booking_state, dict):
                    status = booking_state.get("status")
                    if status in ("collecting", "ready"):
                        intent = "booking"
            except Exception:
                pass

            if intent == "service":
                # Route to service agent
                response = await self.service_agent.get_services(
                    query=message,
                    platform_context=platform_context,
                    service_type="restaurant"
                )
                state["response"] = response.dict()
                # Store entity for follow-ups
                try:
                    services = state["response"].get("services") or []
                    if services:
                        top = services[0]
                        place_name = top.get("name")
                        if place_name:
                            self.memory.set_entities(conversation_id, {
                                "current_place": place_name,
                                "last_mentioned_place": place_name
                            })
                except Exception:
                    pass
                
            elif intent == "booking":
                # Conversational booking flow via BookingAgent
                booking_response = await self.booking_agent.handle(
                    conversation_id=conversation_id,
                    message=message,
                    platform_context=platform_context,
                )
                state["response"] = booking_response.dict()
                
            else:
                # Route to QnA agent
                response = await self.qna_agent.search_embedding(
                    query=message,
                    platform_context=platform_context
                )
                state["response"] = response.dict()
                # Store topic/subject to help resolve follow-ups like "ở đó/cái đó"
                try:
                    sources = state["response"].get("sources") or []
                    top_title = sources[0].get("title") if sources else None
                    subject = top_title or message
                    self.memory.set_entities(conversation_id, {
                        "last_subject": subject,
                        "current_topic": subject
                    })
                except Exception:
                    pass
            
            return state
            
        except Exception as e:
            state["error"] = f"Agent routing error: {str(e)}"
            return state
    
    async def _add_cta(self, state: WorkflowState) -> WorkflowState:
        """Add platform-specific CTA to response"""
        if state.get("error"):
            return state
            
        platform_context = state["platform_context"]
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
            state["error"] = f"CTA generation error: {str(e)}"
            return state
    
    async def _format_response(self, state: WorkflowState) -> WorkflowState:
        """Format final response"""
        if state.get("error"):
            # Create error response
            error_response = ChatResponse(
                type="Error",
                answerAI=f"Xin lỗi, đã xảy ra lỗi: {state['error']}",
                sources=[],
                suggestions=[
                    {
                        "label": "Thử lại",
                        "action": "retry",
                        "data": {}
                    }
                ]
            )
            state["final_response"] = error_response
        else:
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
            final_response=None,
            error=None
        )
        
        # Execute workflow
        try:
            # Save user turn
            conversation_id = getattr(request, "conversationId", None) or "default"
            self.memory.add_turn(conversation_id, "user", request.message)

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
                return ChatResponse(
                    type="Error",
                    answerAI="Xin lỗi, đã xảy ra lỗi không xác định",
                    sources=[],
                    suggestions=[
                        {
                            "label": "Thử lại",
                            "action": "retry",
                            "data": {}
                        }
                    ]
                )
                
        except Exception as e:
            # Handle workflow execution errors
            return ChatResponse(
                type="Error",
                answerAI=f"Xin lỗi, đã xảy ra lỗi hệ thống: {str(e)}",
                sources=[],
                suggestions=[
                    {
                        "label": "Thử lại",
                        "action": "retry",
                        "data": {}
                    }
                ]
            )
    
    def get_workflow_graph(self) -> Dict[str, Any]:
        """Get workflow graph for visualization"""
        return {
            "nodes": [
                {"id": "validate_platform", "type": "validation"},
                {"id": "classify_intent", "type": "classification"},
                {"id": "route_to_agent", "type": "routing"},
                {"id": "add_cta", "type": "enhancement"},
                {"id": "format_response", "type": "formatting"}
            ],
            "edges": [
                {"from": "validate_platform", "to": "classify_intent"},
                {"from": "classify_intent", "to": "route_to_agent"},
                {"from": "route_to_agent", "to": "add_cta"},
                {"from": "add_cta", "to": "format_response"},
                {"from": "format_response", "to": "END"}
            ],
            "conditional_edges": [
                {
                    "from": "validate_platform",
                    "condition": "error",
                    "to": "END"
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
            self.memory.set_entities(conversation_id, entities_update)