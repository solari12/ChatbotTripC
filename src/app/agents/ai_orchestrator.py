#!/usr/bin/env python3
"""
AI Agent Orchestrator - LangGraph-based implementation
Maintains backward compatibility while using modern LangGraph workflow
"""

from typing import Union, Optional
from ..models.schemas import ChatRequest, ChatResponse, QnAResponse, ServiceResponse
from ..models.platform_models import PlatformType, PlatformContext
from ..core.platform_context import PlatformContextHandler
from ..core.cta_engine import CTAEngine
from ..core.langgraph_workflow import LangGraphWorkflow
from .qna_agent import QnAAgent
from .service_agent import ServiceAgent
from ..llm.open_client import OpenAIClient
import logging

logger = logging.getLogger(__name__)


class AIAgentOrchestrator:
    """Orchestrates AI agents with platform-aware routing using LangGraph workflow"""
    
    def __init__(self, qna_agent: QnAAgent, service_agent: ServiceAgent, llm_client: OpenAIClient = None):
        self.qna_agent = qna_agent
        self.service_agent = service_agent
        self.llm_client = llm_client or OpenAIClient()  # Auto-create if not provided
        
        # Initialize LangGraph workflow
        self.langgraph_workflow = LangGraphWorkflow(qna_agent, service_agent, llm_client)
        
        # Keep legacy components for backward compatibility
        self.platform_handler = PlatformContextHandler()
        self.cta_engine = CTAEngine()
        
        # Legacy intent classification keywords (kept for reference)
        self.service_intents = [
            "nhà hàng", "quán ăn", "đồ ăn", "ẩm thực", "restaurant", "food", "dining",
            "tour", "du lịch", "tham quan", "điểm đến", "attraction", "sightseeing",
            "khách sạn", "nơi ở", "accommodation", "hotel", "lodging",
            "tìm", "search", "find", "khám phá", "explore"
        ]
        
        self.booking_intents = [
            "đặt", "book", "reservation", "đặt bàn", "đặt chỗ", "make appointment",
            "đặt tour", "book tour", "đặt phòng", "book room"
        ]
    
    async def process_request(self, request: ChatRequest) -> ChatResponse:
        """Process chat request with LangGraph workflow (main interface)"""
        try:
            # Use LangGraph workflow for processing
            response = await self.langgraph_workflow.process_request(request)
            return response
            
        except Exception as e:
            logger.error(f"Error processing request with LangGraph workflow: {e}")
            # Fallback to legacy processing if LangGraph fails
            return await self._legacy_process_request(request)
    
    async def _legacy_process_request(self, request: ChatRequest) -> ChatResponse:
        """Legacy processing method as fallback"""
        try:
            # Create platform context
            platform_context = self.platform_handler.create_context(request)
            
            # Classify intent using legacy method
            intent = self._classify_intent(request.message)
            
            # Route to appropriate agent
            if intent == "service":
                response = await self._handle_service_intent(request, platform_context)
            elif intent == "booking":
                response = await self._handle_booking_intent(request, platform_context)
            else:
                response = await self._handle_qna_intent(request, platform_context)
            
            # Add platform-specific CTA
            response = await self._add_platform_cta(response, platform_context)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in legacy processing: {e}")
            return await self._get_error_response(request)
    
    def _classify_intent(self, message: str) -> str:
        """Legacy intent classification using keywords"""
        message_lower = message.lower()
        
        # Check for service intent
        if any(keyword in message_lower for keyword in self.service_intents):
            return "service"
        
        # Check for booking intent
        if any(keyword in message_lower for keyword in self.booking_intents):
            return "booking"
        
        # Default to QnA
        return "qna"
    
    async def _handle_service_intent(self, request: ChatRequest, 
                                   platform_context: PlatformContext) -> ServiceResponse:
        """Handle service-related requests"""
        try:
            # Route to service agent
            response = await self.service_agent.get_services(
                query=request.message,
                platform_context=platform_context,
                service_type="restaurant"  # Default to restaurant, can be enhanced
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling service intent: {e}")
            # Fallback to QnA
            return await self._handle_qna_intent(request, platform_context)
    
    async def _handle_booking_intent(self, request: ChatRequest, 
                                    platform_context: PlatformContext) -> QnAResponse:
        """Handle booking-related requests"""
        try:
            # For booking intents, we'll provide guidance and trigger user info collection
            language = platform_context.language.value
            
            if language == "vi":
                answer = "Tôi có thể giúp bạn đặt chỗ! Để tiếp tục, vui lòng cung cấp thông tin của bạn."
            else:
                answer = "I can help you make a booking! To continue, please provide your information."
            
            # Create QnA response with booking suggestions
            suggestions = [
                {
                    "label": "Đặt chỗ ngay" if language == "vi" else "Book now",
                    "detail": "Cung cấp thông tin để đặt chỗ" if language == "vi" else "Provide information to make booking",
                    "action": "collect_user_info"
                }
            ]
            
            sources = [
                {
                    "title": "TripC Booking Service",
                    "url": "https://tripc.ai/booking",
                    "imageUrl": "https://cdn.tripc.ai/sources/booking-service.jpg"
                }
            ]
            
            return QnAResponse(
                type="QnA",
                answerAI=answer,
                sources=sources,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error handling booking intent: {e}")
            # Fallback to QnA
            return await self._handle_qna_intent(request, platform_context)
    
    async def _handle_qna_intent(self, request: ChatRequest, 
                                platform_context: PlatformContext) -> QnAResponse:
        """Handle QnA-related requests"""
        try:
            # Route to QnA agent
            response = await self.qna_agent.search_embedding(
                query=request.message,
                platform_context=platform_context
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling QnA intent: {e}")
            # Return basic fallback response
            return await self._get_fallback_response(platform_context)
    
    async def _add_platform_cta(self, response: Union[QnAResponse, ServiceResponse], 
                               platform_context: PlatformContext) -> Union[QnAResponse, ServiceResponse]:
        """Add platform-specific CTA to response"""
        try:
            # Generate appropriate CTA based on response type and platform
            if hasattr(response, 'services') and response.services:
                # Service response - generate service-specific CTA
                cta = self.cta_engine.generate_service_cta(
                    platform=platform_context.platform,
                    device=platform_context.device,
                    services=response.services
                )
            else:
                # QnA response - generate general platform CTA
                cta = self.cta_engine.generate_platform_cta(
                    platform=platform_context.platform,
                    device=platform_context.device
                )
            
            if cta:
                # Localize CTA based on language
                cta = self.cta_engine.get_cta_for_language(cta, platform_context.language.value)
                
                # Convert CTA to dict format for response
                response.cta = {
                    "device": cta.device.value,
                    "label": cta.label,
                    "url": cta.url,
                    "deeplink": cta.deeplink
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error adding platform CTA: {e}")
            return response
    
    async def _get_error_response(self, request: ChatRequest) -> ChatResponse:
        """Get error response when processing fails"""
        # Try to create basic platform context for error handling
        try:
            platform_context = self.platform_handler.create_context(request)
            language = platform_context.language.value
        except:
            language = "vi"  # Default to Vietnamese
        
        if language == "vi":
            answer = "Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu của bạn. Vui lòng thử lại sau."
        else:
            answer = "Sorry, an error occurred while processing your request. Please try again later."
        
        return ChatResponse(
            type="Error",
            answerAI=answer,
            sources=[],
            suggestions=[]
        )
    
    async def _get_fallback_response(self, platform_context: PlatformContext) -> QnAResponse:
        """Get fallback response when agent processing fails"""
        language = platform_context.language.value
        
        if language == "vi":
            answer = "Xin lỗi, tôi gặp khó khăn khi xử lý yêu cầu của bạn. Bạn có thể thử hỏi lại hoặc sử dụng các tùy chọn bên dưới."
        else:
            answer = "Sorry, I'm having trouble processing your request. You can try asking again or use the options below."
        
        suggestions = [
            {
                "label": "Tìm nhà hàng" if language == "vi" else "Find restaurants",
                "detail": "Khám phá các nhà hàng nổi tiếng" if language == "vi" else "Explore famous restaurants",
                "action": "show_services"
            },
            {
                "label": "Hỗ trợ" if language == "vi" else "Help",
                "detail": "Xem hướng dẫn sử dụng" if language == "vi" else "View usage guide",
                "action": "show_help"
            }
        ]
        
        sources = [
            {
                "title": "TripC Support",
                "url": "https://tripc.ai/support",
                "imageUrl": "https://cdn.tripc.ai/sources/support.jpg"
            }
        ]
        
        return QnAResponse(
            type="QnA",
            answerAI=answer,
            sources=sources,
            suggestions=suggestions
        )
    
    # Additional methods for LangGraph integration
    def get_workflow_graph(self):
        """Get LangGraph workflow visualization"""
        return self.langgraph_workflow.get_workflow_graph()
    
    def get_workflow_stats(self):
        """Get workflow statistics"""
        return {
            "workflow_type": "LangGraph",
            "nodes": 5,
            "has_error_handling": True,
            "has_conditional_edges": True,
            "legacy_fallback": True
        }