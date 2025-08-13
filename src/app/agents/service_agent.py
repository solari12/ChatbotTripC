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
        
        # Service type mappings with comprehensive keywords
        self.service_keywords = {
            "restaurant": [
                "nhà hàng", "quán ăn", "đồ ăn", "ẩm thực", "restaurant", "food", "dining",
                "ăn", "bữa", "món", "nấu", "chế biến", "thực phẩm", "đồ uống", "cafe", "bar"
            ],
            "tour": [
                "tour", "du lịch", "tham quan", "điểm đến", "attraction", "sightseeing",
                "thăm", "khám phá", "địa điểm", "danh lam", "thắng cảnh", "di tích", "bảo tàng",
                "công viên", "bãi biển", "núi", "sông", "hồ", "đảo", "chùa", "nhà thờ"
            ],
            "hotel": [
                "khách sạn", "nơi ở", "accommodation", "hotel", "lodging", "resort",
                "đặt phòng", "nghỉ ngơi", "lưu trú", "homestay", "villa", "căn hộ",
                "hostel", "motel", "bed & breakfast"
            ]
        }
    
    async def get_services(self, query: str, platform_context: PlatformContext, 
                          service_type: str = "restaurant", page: int = 6) -> ServiceResponse:
        """Get services based on query and type with LLM-powered responses"""
        try:
            # Determine service type from query
            detected_type = self._detect_service_type(query)
            if detected_type:
                service_type = detected_type
            
            # Extract search criteria from query
            search_criteria = self._extract_search_criteria(query)
            
            # Get services from TripC API based on service type with search criteria
            if service_type == "restaurant":
                # First try to get restaurants by location (more reliable)
                if search_criteria.get("location"):
                    # Get more pages to find specific cuisine
                    all_services = []
                    for p in range(1, 4):  # Get first 3 pages
                        page_services = await self.tripc_client.get_restaurants(
                            page=p, 
                            page_size=20,
                            city=search_criteria.get("location")
                        )
                        all_services.extend(page_services)
                        if len(page_services) < 20:  # No more results
                            break
                    
                    services = all_services
                    
                    # If cuisine is specified, filter the results
                    if search_criteria.get("cuisine") and services:
                        cuisine_filter = search_criteria.get("cuisine").lower()
                        filtered_services = []
                        for service in services:
                            # Check if cuisine matches in name, description, or product types
                            service_text = f"{service.name} {service.description} {service.productTypes}".lower()
                            
                            # More precise matching for specific cuisines
                            if cuisine_filter == "nhật bản" or cuisine_filter == "japanese":
                                # Look for Japanese-specific keywords
                                japanese_keywords = ["nhật", "japanese", "sushi", "sashimi", "tempura", "ramen", "udon"]
                                if any(keyword in service_text for keyword in japanese_keywords):
                                    filtered_services.append(service)
                            elif cuisine_filter == "italian":
                                # Look for Italian-specific keywords
                                italian_keywords = ["italian", "italy", "pizza", "pasta", "spaghetti", "risotto", "tiramisu"]
                                if any(keyword in service_text for keyword in italian_keywords):
                                    filtered_services.append(service)
                            elif cuisine_filter == "việt nam" or cuisine_filter == "vietnamese":
                                # Look for Vietnamese-specific keywords
                                vietnamese_keywords = ["việt", "vietnamese", "phở", "bún", "bánh", "mì quảng", "cao lầu"]
                                if any(keyword in service_text for keyword in vietnamese_keywords):
                                    filtered_services.append(service)
                            else:
                                # General matching for other cuisines
                                if cuisine_filter in service_text:
                                    filtered_services.append(service)
                        
                        services = filtered_services
                else:
                    # Fallback to keyword search
                    services = await self.tripc_client.get_restaurants(
                        page=page, 
                        page_size=10,
                        keyword=search_criteria.get("cuisine")
                    )
            elif service_type == "tour":
                # For now, return empty list as tour endpoint doesn't exist
                services = []
            elif service_type == "hotel":
                # For now, return empty list as hotel endpoint doesn't exist
                services = []
            else:
                # For other service types, try restaurants as fallback with basic search
                services = await self.tripc_client.get_restaurants(
                    page=page, 
                    page_size=10,
                    keyword=search_criteria.get("cuisine") or search_criteria.get("location")
                )
            
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
                                    city: Optional[str] = None, page: int = 1,
                                    keyword: Optional[str] = None) -> ServiceResponse:
        """Get restaurant services specifically with LLM-powered responses"""
        try:
            services = await self.tripc_client.get_restaurants(
                page=page, 
                city=city,
                keyword=keyword
            )
            
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
        """Detect service type from query text with scoring"""
        query_lower = query.lower()
        scores = {}
        
        # Calculate scores for each service type
        for service_type, keywords in self.service_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in query_lower:
                    score += 1
                    # Bonus for exact matches
                    if keyword in query_lower.split():
                        score += 2
            scores[service_type] = score
        
        # Return service type with highest score
        if scores:
            best_type = max(scores, key=scores.get)
            return best_type if scores[best_type] > 0 else None
        
        return None
    
    def _get_service_type_vietnamese(self, service_type: str) -> str:
        """Convert service type to Vietnamese"""
        type_mapping = {
            "restaurant": "nhà hàng",
            "tour": "điểm du lịch",
            "hotel": "khách sạn",
            "attraction": "điểm tham quan",
            "activity": "hoạt động",
            "transport": "giao thông"
        }
        return type_mapping.get(service_type, service_type)
    
    def _get_service_type_english(self, service_type: str) -> str:
        """Convert service type to English"""
        type_mapping = {
            "restaurant": "restaurants",
            "tour": "tourist attractions",
            "hotel": "hotels",
            "attraction": "attractions",
            "activity": "activities",
            "transport": "transportation"
        }
        return type_mapping.get(service_type, service_type)
    
    async def _generate_llm_response(self, query: str, services: List[Service], 
                                   service_type: str, platform_context: PlatformContext) -> str:
        """Generate intelligent response using LLM based on context"""
        try:
            language = platform_context.language.value
            
            # Create context-aware prompt for LLM
            if language == "vi":
                service_type_vi = self._get_service_type_vietnamese(service_type)
                prompt = f"""Bạn là TripC.AI, trợ lý du lịch thông minh.

Người dùng tìm kiếm: "{query}"
Loại dịch vụ: {service_type_vi}

Dịch vụ phù hợp:
{self._format_services_for_prompt(services, language)}

Trả lời bằng tiếng Việt, tự nhiên, thân thiện, dưới 80 từ. Giới thiệu về {service_type_vi} và nhắc người dùng tải app TripC để xem chi tiết."""
            else:
                service_type_en = self._get_service_type_english(service_type)
                prompt = f"""You are TripC.AI, an intelligent travel assistant.

User search: "{query}"
Service type: {service_type_en}

Matching services:
{self._format_services_for_prompt(services, language)}

Respond in English, naturally, friendly, under 80 words. Introduce {service_type_en} and remind user to download TripC app for details."""
            
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
                prompt = f"""Bạn là TripC.AI, trợ lý du lịch thông minh.

Người dùng tìm kiếm nhà hàng tại {location}

Nhà hàng nổi bật:
{self._format_services_for_prompt(services, language)}

Trả lời bằng tiếng Việt, tự nhiên, thân thiện, dưới 80 từ. Giới thiệu ẩm thực {location} và nhắc tải app TripC để đặt bàn."""
            else:
                location = city if city else "Da Nang"
                prompt = f"""You are TripC.AI, an intelligent travel assistant.

User looking for restaurants in {location}

Featured restaurants:
{self._format_services_for_prompt(services, language)}

Respond in English, naturally, friendly, under 80 words. Introduce {location} cuisine and remind to download TripC app for booking."""
            
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
        service_list = []
        for i, service in enumerate(services[:3], 1):  # Limit to first 3 for cleaner prompt
            name = service.name
            description = service.description[:80] if service.description else ""
            address = service.address if service.address else ""
            city = service.city if service.city else ""
            rating = service.rating if service.rating else None
            product_types = service.productTypes if service.productTypes else ""
            working_hours = service.workingHoursDisplay if service.workingHoursDisplay else ""
            
            if language == "vi":
                service_info = f"{i}. {name}"
                if product_types:
                    service_info += f" ({product_types})"
                if description:
                    service_info += f" - {description}"
                if address:
                    service_info += f" - {address}"
                if city and city not in address:
                    service_info += f", {city}"
                if rating:
                    service_info += f" - ⭐ {rating}/5"
                if working_hours:
                    service_info += f" - Giờ: {working_hours}"
            else:
                service_info = f"{i}. {name}"
                if product_types:
                    service_info += f" ({product_types})"
                if description:
                    service_info += f" - {description}"
                if address:
                    service_info += f" - {address}"
                if city and city not in address:
                    service_info += f", {city}"
                if rating:
                    service_info += f" - ⭐ {rating}/5"
                if working_hours:
                    service_info += f" - Hours: {working_hours}"
            
            service_list.append(service_info)
        
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
                # For other service types, return None as endpoints don't exist yet
                logger.warning(f"Service detail endpoint for {service_type} not implemented yet")
                return None
                
        except Exception as e:
            logger.error(f"Error getting service detail: {e}")
            return None
    
    def _extract_search_criteria(self, query: str) -> Dict[str, str]:
        """Extract search criteria from user query"""
        query_lower = query.lower()
        criteria = {}
        
        # Extract location/city (expanded list)
        location_keywords = {
            "đà nẵng": "đà nẵng", "da nang": "đà nẵng", "danang": "đà nẵng",
            "hội an": "hội an", "hoi an": "hội an", "hoian": "hội an",
            "huế": "huế", "hue": "huế", "hue city": "huế",
            "sài gòn": "sài gòn", "saigon": "sài gòn", "hồ chí minh": "sài gòn", "ho chi minh": "sài gòn",
            "hà nội": "hà nội", "hanoi": "hà nội", "hà nội": "hà nội",
            "nha trang": "nha trang", "vũng tàu": "vũng tàu", "vung tau": "vũng tàu",
            "phú quốc": "phú quốc", "phu quoc": "phú quốc", "đà lạt": "đà lạt", "dalat": "đà lạt"
        }
        
        for location_key, location_value in location_keywords.items():
            if location_key in query_lower:
                criteria["location"] = location_value
                break
        
        # Extract cuisine type (expanded list)
        cuisine_keywords = {
            # Vietnamese
            "hải sản": "hải sản", "seafood": "hải sản", "tôm": "hải sản", "cua": "hải sản", "cá": "hải sản",
            "việt nam": "việt nam", "vietnamese": "việt nam", "phở": "việt nam", "bún": "việt nam", "bánh": "việt nam",
            "mì quảng": "việt nam", "bánh xèo": "việt nam", "lẩu": "việt nam", "bún bò": "việt nam",
            
            # International
            "trung quốc": "trung quốc", "chinese": "trung quốc", "dimsum": "trung quốc", "mì xào": "trung quốc",
            "hàn quốc": "hàn quốc", "korean": "hàn quốc", "bbq": "hàn quốc", "kimchi": "hàn quốc",
            "nhật bản": "nhật bản", "japanese": "nhật bản", "sushi": "nhật bản", "sashimi": "nhật bản",
            "italy": "italian", "italian": "italian", "pizza": "italian", "pasta": "italian", "ý": "italian",
            "pháp": "pháp", "french": "pháp", "bánh mì": "pháp",
            "thái": "thái", "thai": "thái", "tom yum": "thái", "pad thai": "thái",
            
            # Special diets
            "món chay": "món chay", "vegetarian": "món chay", "chay": "món chay",
            "vegan": "món chay", "không thịt": "món chay",
            
            # Drinks
            "cafe": "cafe", "coffee": "cafe", "trà sữa": "trà sữa", "bubble tea": "trà sữa",
            "soda": "soda", "nước ép": "nước ép", "juice": "nước ép"
        }
        
        for cuisine_key, cuisine_value in cuisine_keywords.items():
            if cuisine_key in query_lower:
                criteria["cuisine"] = cuisine_value
                break
        
        # Extract price range
        if any(word in query_lower for word in ["rẻ", "cheap", "giá rẻ", "affordable", "bình dân", "dân dã"]):
            criteria["price_range"] = "low"
        elif any(word in query_lower for word in ["đắt", "expensive", "cao cấp", "luxury", "premium", "sang trọng"]):
            criteria["price_range"] = "high"
        elif any(word in query_lower for word in ["trung bình", "moderate", "vừa phải"]):
            criteria["price_range"] = "medium"
        
        # Extract rating preference
        if any(word in query_lower for word in ["ngon", "tốt", "good", "best", "nổi tiếng", "famous", "được đánh giá cao"]):
            criteria["rating"] = "high"
        
        # Extract meal time
        if any(word in query_lower for word in ["sáng", "breakfast", "bữa sáng"]):
            criteria["meal_time"] = "breakfast"
        elif any(word in query_lower for word in ["trưa", "lunch", "bữa trưa"]):
            criteria["meal_time"] = "lunch"
        elif any(word in query_lower for word in ["tối", "dinner", "bữa tối", "tối nay"]):
            criteria["meal_time"] = "dinner"
        
        # Extract special requirements
        if any(word in query_lower for word in ["gần đây", "nearby", "gần", "close"]):
            criteria["distance"] = "nearby"
        if any(word in query_lower for word in ["view", "view đẹp", "nhìn ra biển", "ocean view"]):
            criteria["view"] = "ocean"
        if any(word in query_lower for word in ["romantic", "lãng mạn", "date", "hẹn hò"]):
            criteria["atmosphere"] = "romantic"
        
        return criteria
    
