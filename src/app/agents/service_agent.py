from typing import List, Optional, Dict, Any
from ..models.schemas import ServiceResponse, Service, Source, Suggestion
from ..services.tripc_api import TripCAPIClient
from ..core.platform_context import PlatformContext
from ..llm.open_client import OpenAIClient
import logging

logger = logging.getLogger(__name__)


class ServiceAgent:
    """Service Agent for TripC API integration with app-first policy and LLM-powered responses"""
    
    def __init__(self, tripc_client: TripCAPIClient, llm_client: OpenAIClient = None):
        self.tripc_client = tripc_client
        self.llm_client = llm_client or OpenAIClient()  # Auto-create if not provided
        
        # Service type mappings
        self.service_keywords = {
            "restaurant": ["nhà hàng", "quán ăn", "đồ ăn", "ẩm thực", "restaurant", "food", "dining"],
            "tour": ["tour", "du lịch", "tham quan", "điểm đến", "attraction", "sightseeing"],
            "hotel": ["khách sạn", "nơi ở", "accommodation", "hotel", "lodging"]
        }
    
    async def get_services(self, query: str, platform_context: PlatformContext, 
                          service_type: str = "restaurant", page: int = 1) -> ServiceResponse:
        """Get services based on query and type with LLM-powered responses"""
        try:
            # Determine service type from query
            detected_type = self._detect_service_type(query)
            if detected_type:
                service_type = detected_type
            
            # Get services from TripC API
            if service_type == "restaurant":
                services = await self.tripc_client.get_restaurants(page=page, page_size=10)
            else:
                services = await self.tripc_client.search_services(query, service_type, page=page)
            
            if not services:
                return await self._get_no_services_response(platform_context, service_type)
            
            # Generate intelligent response using LLM
            answer_ai = await self._generate_llm_response(query, services, service_type, platform_context)
            sources = self.tripc_client.get_service_sources()
            suggestions = self._generate_service_suggestions(platform_context, service_type)
            
            return ServiceResponse(
                type="Service",
                answerAI=answer_ai,
                services=services,
                sources=sources,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error getting services: {e}")
            return await self._get_error_response(platform_context, service_type)
    
    async def get_restaurant_services(self, platform_context: PlatformContext, 
                                    city: Optional[str] = None, page: int = 1) -> ServiceResponse:
        """Get restaurant services specifically with LLM-powered responses"""
        try:
            services = await self.tripc_client.get_restaurants(page=page, city=city)
            
            if not services:
                return await self._get_no_services_response(platform_context, "restaurant")
            
            # Generate intelligent response using LLM
            answer_ai = await self._generate_restaurant_llm_response(services, platform_context, city)
            sources = self.tripc_client.get_service_sources()
            suggestions = self._generate_service_suggestions(platform_context, "restaurant")
            
            return ServiceResponse(
                type="Service",
                answerAI=answer_ai,
                services=services,
                sources=sources,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error getting restaurant services: {e}")
            return await self._get_error_response(platform_context, "restaurant")
    
    def _detect_service_type(self, query: str) -> Optional[str]:
        """Detect service type from query text"""
        query_lower = query.lower()
        
        for service_type, keywords in self.service_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return service_type
        
        return None
    
    async def _generate_llm_response(self, query: str, services: List[Service], 
                                   service_type: str, platform_context: PlatformContext) -> str:
        """Generate intelligent response using LLM based on context"""
        try:
            language = platform_context.language.value
            
            # Create context-aware prompt for LLM
            if language == "vi":
                prompt = f"""
                Bạn là một trợ lý du lịch thông minh của TripC. Người dùng đang tìm kiếm dịch vụ {service_type} với yêu cầu: "{query}".

                Dưới đây là danh sách các dịch vụ phù hợp:
                {self._format_services_for_prompt(services, language)}
                
                Hãy tạo một câu trả lời thông minh, thân thiện và hữu ích bằng tiếng Việt. 
                Câu trả lời nên:
                - Chào hỏi người dùng một cách thân thiện
                - Giải thích tại sao những dịch vụ này phù hợp với yêu cầu
                - Đưa ra gợi ý hoặc lời khuyên hữu ích
                - Khuyến khích người dùng tải app TripC để xem chi tiết
                
                Trả lời ngắn gọn, tự nhiên và không quá 100 từ.
                """
            else:
                prompt = f"""
                You are an intelligent travel assistant from TripC. The user is looking for {service_type} services with the request: "{query}".

                Here are the matching services:
                {self._format_services_for_prompt(services, language)}
                
                Please create an intelligent, friendly, and helpful response in English.
                The response should:
                - Greet the user warmly
                - Explain why these services match their request
                - Provide helpful suggestions or advice
                - Encourage downloading the TripC app for details
                
                Keep it concise, natural, and under 100 words.
                """
            
            # Generate response using LLM
            llm_response = self.llm_client.generate_response(prompt, max_tokens=150)
            
            if llm_response:
                return llm_response
            else:
                # If LLM fails, create a simple but natural response
                return self._create_simple_response(query, services, service_type, platform_context)
                
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            # Create simple response as fallback
            return self._create_simple_response(query, services, service_type, platform_context)
    
    async def _generate_restaurant_llm_response(self, services: List[Service], 
                                             platform_context: PlatformContext, 
                                             city: Optional[str] = None) -> str:
        """Generate intelligent restaurant response using LLM"""
        try:
            language = platform_context.language.value
            
            # Create context-aware prompt for LLM
            if language == "vi":
                location = city if city else "Đà Nẵng"
                prompt = f"""
                Bạn là một trợ lý du lịch thông minh của TripC. Người dùng đang tìm kiếm nhà hàng tại {location}.

                Dưới đây là danh sách các nhà hàng tuyệt vời:
                {self._format_services_for_prompt(services, language)}
                
                Hãy tạo một câu trả lời thông minh, thân thiện và hữu ích bằng tiếng Việt.
                Câu trả lời nên:
                - Chào hỏi người dùng một cách thân thiện
                - Giới thiệu về ẩm thực tại {location}
                - Đưa ra gợi ý về việc chọn nhà hàng
                - Khuyến khích tải app TripC để xem chi tiết và đặt bàn
                
                Trả lời ngắn gọn, tự nhiên và không quá 100 từ.
                """
            else:
                location = city if city else "Da Nang"
                prompt = f"""
                You are an intelligent travel assistant from TripC. The user is looking for restaurants in {location}.

                Here are some great restaurants:
                {self._format_services_for_prompt(services, language)}
                
                Please create an intelligent, friendly, and helpful response in English.
                The response should:
                - Greet the user warmly
                - Introduce the culinary scene in {location}
                - Provide suggestions for choosing restaurants
                - Encourage downloading the TripC app for details and booking
                
                Keep it concise, natural, and under 100 words.
                """
            
            # Generate response using LLM
            llm_response = self.llm_client.generate_response(prompt, max_tokens=150)
            
            if llm_response:
                return llm_response
            else:
                # If LLM fails, create a simple but natural response
                return self._create_simple_restaurant_response(services, platform_context, city)
                
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            # Create simple response as fallback
            return self._create_simple_restaurant_response(services, platform_context, city)
    
    def _create_simple_response(self, query: str, services: List[Service], 
                              service_type: str, platform_context: PlatformContext) -> str:
        """Create a simple but natural response when LLM fails"""
        language = platform_context.language.value
        
        if language == "vi":
            service_names = ", ".join([service.name for service in services[:3]])
            return f"Chào bạn! Tôi đã tìm thấy những dịch vụ {service_type} phù hợp với yêu cầu '{query}'. Dưới đây là một số gợi ý: {service_names}. Để xem chi tiết và đặt chỗ, hãy tải app TripC nhé!"
        else:
            service_names = ", ".join([service.name for service in services[:3]])
            return f"Hello! I found some great {service_type} services that match your request '{query}'. Here are some suggestions: {service_names}. To see details and make bookings, please download the TripC app!"
    
    def _create_simple_restaurant_response(self, services: List[Service], 
                                         platform_context: PlatformContext, 
                                         city: Optional[str] = None) -> str:
        """Create a simple but natural restaurant response when LLM fails"""
        language = platform_context.language.value
        location = city if city else ("Đà Nẵng" if language == "vi" else "Da Nang")
        
        if language == "vi":
            service_names = ", ".join([service.name for service in services[:3]])
            return f"Chào bạn! Đây là những nhà hàng tuyệt vời tại {location}: {service_names}. Những địa điểm này nổi tiếng với ẩm thực ngon và không gian đẹp. Để xem menu và đặt bàn, hãy tải app TripC!"
        else:
            service_names = ", ".join([service.name for service in services[:3]])
            return f"Hello! Here are some excellent restaurants in {location}: {service_names}. These places are known for great food and beautiful atmospheres. To see menus and make reservations, please download the TripC app!"
    
    def _format_services_for_prompt(self, services: List[Service], language: str) -> str:
        """Format services list for LLM prompt"""
        if language == "vi":
            service_list = []
            for i, service in enumerate(services[:5], 1):  # Limit to first 5 for prompt
                service_list.append(f"{i}. {service.name} - {service.description[:100]}...")
            return "\n".join(service_list)
        else:
            service_list = []
            for i, service in enumerate(services[:5], 1):
                service_list.append(f"{i}. {service.name} - {service.description[:100]}...")
            return "\n".join(service_list)
    
    def _generate_service_suggestions(self, platform_context: PlatformContext, 
                                    service_type: str) -> List[Suggestion]:
        """Generate platform-aware service suggestions"""
        language = platform_context.language.value
        
        if language == "vi":
            suggestions = [
                Suggestion(
                    label="Đặt chỗ ngay",
                    detail="Đặt bàn tại nhà hàng yêu thích",
                    action="collect_user_info"
                ),
                Suggestion(
                    label="Xem thêm dịch vụ",
                    detail="Khám phá các dịch vụ khác",
                    action="show_more_services"
                ),
                Suggestion(
                    label="Tìm kiếm khác",
                    detail="Tìm kiếm với tiêu chí khác",
                    action="search_services"
                )
            ]
        else:
            suggestions = [
                Suggestion(
                    label="Book now",
                    detail="Make a reservation at your favorite restaurant",
                    action="collect_user_info"
                ),
                Suggestion(
                    label="View more services",
                    detail="Explore other services",
                    action="show_more_services"
                ),
                Suggestion(
                    label="Search again",
                    detail="Search with different criteria",
                    action="search_services"
                )
            ]
        
        return suggestions
    
    async def _get_no_services_response(self, platform_context: PlatformContext, 
                                      service_type: str) -> ServiceResponse:
        """Get response when no services are found"""
        language = platform_context.language.value
        
        if language == "vi":
            answer = f"Xin lỗi, tôi không tìm thấy dịch vụ {service_type} nào phù hợp với yêu cầu của bạn."
        else:
            answer = f"Sorry, I couldn't find any {service_type} services that match your request."
        
        sources = self.tripc_client.get_service_sources()
        suggestions = [
            Suggestion(
                label="Thử tìm kiếm khác" if language == "vi" else "Try different search",
                detail="Tìm kiếm với từ khóa khác" if language == "vi" else "Search with different keywords",
                action="search_services"
            )
        ]
        
        return ServiceResponse(
            type="Service",
            answerAI=answer,
            services=[],
            sources=sources,
            suggestions=suggestions
        )
    
    async def _get_error_response(self, platform_context: PlatformContext, 
                                service_type: str) -> ServiceResponse:
        """Get response when API error occurs"""
        language = platform_context.language.value
        
        if language == "vi":
            answer = f"Xin lỗi, có lỗi xảy ra khi tìm kiếm dịch vụ {service_type}. Vui lòng thử lại sau."
        else:
            answer = f"Sorry, an error occurred while searching for {service_type} services. Please try again later."
        
        sources = self.tripc_client.get_service_sources()
        suggestions = [
            Suggestion(
                label="Thử lại" if language == "vi" else "Try again",
                detail="Tìm kiếm lại dịch vụ" if language == "vi" else "Search services again",
                action="search_services"
            )
        ]
        
        return ServiceResponse(
            type="Service",
            answerAI=answer,
            services=[],
            sources=sources,
            suggestions=suggestions
        )
    
    async def get_service_detail(self, service_id: int, service_type: str = "restaurant") -> Optional[Service]:
        """Get detailed service information"""
        try:
            if service_type == "restaurant":
                return await self.tripc_client.get_restaurant_detail(service_id)
            else:
                # For other service types, use search with specific ID
                services = await self.tripc_client.search_services(
                    str(service_id), service_type, page=1, page_size=1
                )
                return services[0] if services else None
                
        except Exception as e:
            logger.error(f"Error getting service detail: {e}")
            return None