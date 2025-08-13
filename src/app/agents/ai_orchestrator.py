#!/usr/bin/env python3
"""
AI Agent Orchestrator - LangGraph-based workflow for TripC.AI Chatbot
Replaces the traditional orchestrator with a visual workflow
"""

from typing import Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END

from ..models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType
from ..models.schemas import ChatRequest, ChatResponse, QnAResponse
from ..agents.qna_agent import QnAAgent
from ..agents.service_agent import ServiceAgent
from ..core.cta_engine import CTAEngine

from ..llm.open_client import OpenAIClient


class WorkflowState(TypedDict):
    """State for the LangGraph workflow"""
    # Input
    message: str
    platform: str
    device: str
    language: str
    
    # Processing
    platform_context: Optional[PlatformContext]
    intent: Optional[str]
    response: Optional[Dict[str, Any]]
    
    # Output
    final_response: Optional[ChatResponse]
    error: Optional[str]


class AIAgentOrchestrator:
    """AI Agent Orchestrator - LangGraph-based workflow for TripC.AI Chatbot"""
    
    def __init__(self, qna_agent: QnAAgent, service_agent: ServiceAgent, llm_client: OpenAIClient = None):
        self.qna_agent = qna_agent
        self.service_agent = service_agent
        self.llm_client = llm_client or OpenAIClient()  # Auto-create if not provided
        self.cta_engine = CTAEngine()

        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create the workflow
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("validate_platform", self._validate_platform)
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("route_to_agent", self._route_to_agent)
        workflow.add_node("add_cta", self._add_cta)
        workflow.add_node("format_response", self._format_response)
        
        # Add edges
        workflow.set_entry_point("validate_platform")
        workflow.add_edge("validate_platform", "classify_intent")
        workflow.add_edge("classify_intent", "route_to_agent")
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
                system_prompt = """Phân loại nhanh ý định người dùng:
- "service": TÌM KIẾM nhà hàng, khách sạn, tour, địa điểm
- "booking": ĐẶT CHỖ, đặt bàn, book tour, thanh toán  
- "qna": HỎI THÔNG TIN, tư vấn, giới thiệu, giá vé, giờ mở cửa

Trả về 1 từ: service/booking/qna"""
                user_prompt = f"'{message}' →"
            else:
                system_prompt = """Quick intent classification:
- "service": SEARCH restaurants, hotels, tours, places
- "booking": BOOK, reserve, pay, transaction
- "qna": ASK info, advice, prices, hours, general

Return 1 word: service/booking/qna"""
                user_prompt = f"'{message}' →"
            
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
    
    def _fallback_keyword_classification(self, message: str) -> str:
        """Fallback keyword-based intent classification when LLM is unavailable"""
        message_lower = message.lower()
        
        # Service intent keywords - tìm kiếm, khám phá, xem danh sách
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
            "xung quanh", "around", "khu vực", "area", "đường", "street"
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
            "chính sách", "policy", "điều kiện", "condition", "quy định", "rule"
        ]
        
        # Check for QnA intent first (câu hỏi thông tin có priority cao)
        qna_indicators = [
            "giới thiệu về", "introduce about", "thông tin về", "info about",
            "có gì", "what is", "là gì", "what's", "như thế nào", "how is",
            "bảo tàng", "museum", "di tích", "heritage", "di sản", "heritage site"
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
        
        try:
            if intent == "service":
                # Route to service agent
                response = await self.service_agent.get_services(
                    query=message,
                    platform_context=platform_context,
                    service_type="restaurant"
                )
                state["response"] = response.dict()
                
            elif intent == "booking":
                # For booking, we'll provide a response with suggestions
                # but the actual booking happens via separate endpoint
                response = QnAResponse(
                    type="QnA",
                    answerAI="Tôi hiểu bạn muốn đặt chỗ. Vui lòng cung cấp thông tin chi tiết để tôi có thể hỗ trợ bạn tốt nhất.",
                    sources=[],
                    suggestions=[
                        {
                            "label": "Cung cấp thông tin đặt chỗ",
                            "action": "collect_user_info",
                            "data": {"intent": "booking"}
                        }
                    ]
                )
                state["response"] = response.dict()
                
            else:
                # Route to QnA agent
                response = await self.qna_agent.search_embedding(
                    query=message,
                    platform_context=platform_context
                )
                state["response"] = response.dict()
            
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
            platform_context=None,
            intent=None,
            response=None,
            final_response=None,
            error=None
        )
        
        # Execute workflow
        try:
            # Run the workflow
            result = await self.workflow.ainvoke(initial_state)
            
            # Return final response
            if result.get("final_response"):
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