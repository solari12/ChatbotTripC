#!/usr/bin/env python3
"""
LangGraph Workflow for TripC.AI Chatbot
Replaces the AI Agent Orchestrator with a visual workflow
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


class LangGraphWorkflow:
    """LangGraph-based workflow for TripC.AI Chatbot"""
    
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
            
            # Use direct prompts for intent classification
            if language == "vi":
                system_prompt = """Bạn là một trợ lý AI thông minh. Hãy phân loại ý định của người dùng thành một trong các loại sau:
                - "service": Khi người dùng muốn tìm kiếm, khám phá hoặc xem thông tin về nhà hàng, địa điểm du lịch
                - "booking": Khi người dùng muốn đặt chỗ, đặt bàn, đặt tour hoặc thực hiện giao dịch
                - "qna": Khi người dùng hỏi thông tin chung, tư vấn hoặc không rõ ý định
                
                Chỉ trả về một từ: service, booking, hoặc qna."""
                user_prompt = f"Phân loại ý định: {message}"
            else:
                system_prompt = """You are an intelligent AI assistant. Classify the user's intent into one of the following types:
                - "service": When the user wants to search, explore, or view information about restaurants, tourist attractions
                - "booking": When the user wants to make reservations, book tables, book tours, or perform transactions
                - "qna": When the user asks general information, seeks advice, or intent is unclear
                
                Return only one word: service, booking, or qna."""
                user_prompt = f"Classify intent: {message}"
            
            # Use LLM to classify intent
            if self.llm_client:
                try:
                    # Get LLM response for intent classification
                    combined_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
                    llm_response = self.llm_client.generate_response(
                        prompt=combined_prompt,
                        model="gpt-3.5-turbo",  # Use appropriate model
                        max_tokens=10
                    )
                    
                    # Extract intent from LLM response
                    intent_response = llm_response.strip().lower() if llm_response else ""
                    
                    # Validate and map intent
                    if "service" in intent_response:
                        state["intent"] = "service"
                    elif "booking" in intent_response:
                        state["intent"] = "booking"
                    elif "qna" in intent_response:
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
        
        # Service intent keywords
        service_keywords = [
            "nhà hàng", "restaurant", "quán ăn", "địa điểm", "place",
            "tìm", "search", "khám phá", "explore", "địa chỉ", "address",
            "ở đâu", "where", "gần đây", "nearby", "khuyến mãi", "promotion"
        ]
        
        # Booking intent keywords
        booking_keywords = [
            "đặt", "book", "reserve", "đặt bàn", "booking", "reservation",
            "đặt chỗ", "đặt tour", "book tour", "đặt vé", "book ticket",
            "đặt phòng", "book room", "thanh toán", "payment", "giá", "price"
        ]
        
        # Check for service intent
        if any(keyword in message_lower for keyword in service_keywords):
            return "service"
        # Check for booking intent
        elif any(keyword in message_lower for keyword in booking_keywords):
            return "booking"
        else:
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
            
            response["cta"] = cta.dict()
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
