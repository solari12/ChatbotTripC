from typing import List, Optional, Dict, Any
from ..models.schemas import ServiceResponse, Service, Source, Suggestion
from ..services.tripc_api import TripCAPIClient
from ..core.platform_context import PlatformContext
import logging

logger = logging.getLogger(__name__)


class ServiceAgent:
    """Service Agent for TripC API integration with app-first policy"""
    
    def __init__(self, tripc_client: TripCAPIClient):
        self.tripc_client = tripc_client
        
        # Service type mappings
        self.service_keywords = {
            "restaurant": ["nhà hàng", "quán ăn", "đồ ăn", "ẩm thực", "restaurant", "food", "dining"],
            "tour": ["tour", "du lịch", "tham quan", "điểm đến", "attraction", "sightseeing"],
            "hotel": ["khách sạn", "nơi ở", "accommodation", "hotel", "lodging"]
        }
    
    async def get_services(self, query: str, platform_context: PlatformContext, 
                          service_type: str = "restaurant", page: int = 1) -> ServiceResponse:
        """Get services based on query and type"""
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
            
            # Format response
            answer_ai = self._format_service_answer(query, services, service_type, platform_context)
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
        """Get restaurant services specifically"""
        try:
            services = await self.tripc_client.get_restaurants(page=page, city=city)
            
            if not services:
                return await self._get_no_services_response(platform_context, "restaurant")
            
            # Format response
            answer_ai = self._format_restaurant_answer(services, platform_context, city)
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
    
    def _format_service_answer(self, query: str, services: List[Service], 
                             service_type: str, platform_context: PlatformContext) -> str:
        """Format service answer based on platform context and language"""
        language = platform_context.language.value
        
        if language == "vi":
            if service_type == "restaurant":
                return f"Dưới đây là những nhà hàng tuyệt vời tại Đà Nẵng phù hợp với yêu cầu '{query}':"
            elif service_type == "tour":
                return f"Dưới đây là những tour du lịch hấp dẫn tại Đà Nẵng phù hợp với yêu cầu '{query}':"
            else:
                return f"Dưới đây là những dịch vụ {service_type} phù hợp với yêu cầu '{query}':"
        else:
            if service_type == "restaurant":
                return f"Here are some great restaurants in Da Nang that match your request '{query}':"
            elif service_type == "tour":
                return f"Here are some exciting tours in Da Nang that match your request '{query}':"
            else:
                return f"Here are some {service_type} services that match your request '{query}':"
    
    def _format_restaurant_answer(self, services: List[Service], 
                                platform_context: PlatformContext, city: Optional[str] = None) -> str:
        """Format restaurant-specific answer"""
        language = platform_context.language.value
        
        if language == "vi":
            if city:
                return f"Dưới đây là những nhà hàng tuyệt vời tại {city}:"
            else:
                return "Dưới đây là những nhà hàng tuyệt vời tại Đà Nẵng:"
        else:
            if city:
                return f"Here are some great restaurants in {city}:"
            else:
                return "Here are some great restaurants in Da Nang:"
    
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