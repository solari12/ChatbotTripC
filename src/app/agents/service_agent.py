from typing import List, Optional, Dict, Any
from ..models.schemas import ServiceResponse, Service, Source, Suggestion
from ..services.tripc_api import TripCAPIClient
from ..services.keyword_analyzer import KeywordAnalyzer
from ..core.platform_context import PlatformContext
from ..llm.rate_limited_client import RateLimitedLLMClient
import logging

logger = logging.getLogger(__name__)


class ServiceAgent:
    """Service Agent for TripC API integration with app-first policy and LLM-powered responses"""
    
    def __init__(self, tripc_client: TripCAPIClient, llm_client: RateLimitedLLMClient = None):
        self.tripc_client = tripc_client
        self.llm_client = llm_client
        if llm_client is None:
            from ..llm.open_client import OpenAIClient
            base_llm_client = OpenAIClient()
            self.llm_client = RateLimitedLLMClient(base_llm_client)
        self.keyword_analyzer = KeywordAnalyzer(self.llm_client, self.tripc_client)
        
        # Service type mappings with comprehensive keywords
        self.service_keywords = {
            "restaurant": [
                "nhà hàng", "quán ăn", "đồ ăn", "ẩm thực", "restaurant", "food", "dining",
                "ăn", "bữa", "món", "nấu", "chế biến", "thực phẩm", "đồ uống", "cafe", "bar",
                "bún", "phở", "bánh", "mì", "cơm", "lẩu", "nướng", "hải sản", "việt nam",
                "nhậu", "quán nhậu", "craft beer"
            ],
            "culinary_passport": [
                "hộ chiếu ẩm thực", "culinary passport", "hộ chiếu", "passport", 
                "ẩm thực đà nẵng", "da nang culinary", "đặc sản đà nẵng",
                "bún", "phở", "bánh", "mì", "lẩu", "nướng", "hải sản", "việt nam",
                "seal", "con dấu", "chứng nhận", "certified"
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
            
            # Use LLM to extract search parameters intelligently
            search_params = await self._extract_search_params_with_llm(query, platform_context)
            
            # Get services from TripC API based on service type with LLM-extracted parameters
            if service_type == "restaurant":
                # Use KeywordAnalyzer for intelligent restaurant search
                try:
                    search_result = await self.keyword_analyzer.search_restaurants_with_analysis(
                        user_query=query,
                        page=1,
                        page_size=15
                    )
                    services = search_result["restaurants"]
                    
                    # If no results from KeywordAnalyzer, fallback to old method
                    if not services:
                        logger.warning("No results from KeywordAnalyzer, using fallback method")
                        services = await self.tripc_client.get_restaurants(
                            page=1, 
                            page_size=10,
                            city=search_params.get("city"),
                            keyword=search_params.get("keyword"),
                            supplier_type_slug="am-thuc"
                        )
                        # Limit fallback results to 5
                        services = services[:5]
                    
                except Exception as e:
                    logger.error(f"Error using KeywordAnalyzer: {e}")
                    # Fallback to old method
                    services = await self.tripc_client.get_restaurants(
                        page=1, 
                        page_size=10,
                        city=search_params.get("city"),
                        keyword=search_params.get("keyword"),
                        supplier_type_slug="am-thuc"
                    )
                    services = services[:5]
            elif service_type == "culinary_passport":
                # Use culinary passport suppliers API with keyword and product_type filtering
                keyword = search_params.get("keyword")
                product_type_id = search_params.get("product_type_id")
                
                services = await self.tripc_client.get_culinary_passport_suppliers(
                    page=1,
                    page_size=20,  # Get more for better filtering
                    keyword=keyword,
                    product_type_id=product_type_id
                )
                
                # Apply LLM context filtering for additional refinement
                services = self._filter_services_by_llm_context(services, search_params.get("llm_context", {}))
                
                # Filter by location if specified
                if search_params.get("city") and services:
                    location_filter = search_params.get("city").lower()
                    services = [s for s in services if location_filter in (s.city or "").lower() or location_filter in (s.address or "").lower()]
                # De-duplicate and sort by rating
                if services:
                    unique = {}
                    for s in services:
                        key = (s.name or "").strip().lower() + "|" + (s.address or "").strip().lower()
                        if key not in unique:
                            unique[key] = s
                    services = list(unique.values())
                    services.sort(key=lambda x: (x.rating is not None, x.rating or 0), reverse=True)
                
                # Limit to 5 for response
                services = services[:5]
            elif service_type == "hotel":
                # Use hotels API with luu-tru filter and LLM parameters
                services = await self.tripc_client.get_hotels(
                    page=1,
                    page_size=20  # Get more for better filtering
                )
                # Apply LLM context filtering
                services = self._filter_services_by_llm_context(services, search_params.get("llm_context", {}))
                
                # Filter by location if specified
                if search_params.get("city") and services:
                    location_filter = search_params.get("city").lower()
                    services = [s for s in services if location_filter in (s.city or "").lower() or location_filter in (s.address or "").lower()]
                # De-duplicate and sort by rating
                if services:
                    unique = {}
                    for s in services:
                        key = (s.name or "").strip().lower() + "|" + (s.address or "").strip().lower()
                        if key not in unique:
                            unique[key] = s
                    services = list(unique.values())
                    services.sort(key=lambda x: (x.rating is not None, x.rating or 0), reverse=True)
                
                # Limit to 5 for response
                services = services[:5]
            else:
                # For other service types, fallback to restaurants
                services = await self.tripc_client.get_restaurants(
                    page=1, 
                    page_size=5,
                    keyword=search_params.get("keyword"),
                    city=search_params.get("city")
                )
            
            if not services:
                return await self._get_no_services_response(platform_context, service_type)
            
            # Generate intelligent response using LLM
            answer_ai = await self._generate_llm_response(query, services, service_type, platform_context)
            sources = self.tripc_client.get_service_sources(service_type)
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
            sources = self.tripc_client.get_service_sources("restaurant")
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
            "culinary_passport": "nhà hàng trong Hộ chiếu ẩm thực",
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
            "culinary_passport": "culinary passport restaurants",
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

Trả lời bằng tiếng Việt, tự nhiên, thân thiện, dưới 100 từ. Giới thiệu về {service_type_vi} và nhắc người dùng tải app TripC để xem chi tiết.

QUAN TRỌNG: Nếu đây là tìm kiếm nhà hàng (restaurant), hãy kết thúc câu trả lời bằng: "Bạn cũng có thể tham khảo Hộ chiếu ẩm thực Đà Nẵng để tìm những nhà hàng được chứng nhận chất lượng cao!"."""
            else:
                service_type_en = self._get_service_type_english(service_type)
                prompt = f"""You are TripC.AI, an intelligent travel assistant.

User search: "{query}"
Service type: {service_type_en}

Matching services:
{self._format_services_for_prompt(services, language)}

Respond in English, naturally, friendly, under 100 words. Introduce {service_type_en} and remind user to download TripC app for details.

IMPORTANT: If this is a restaurant search, end your response with: "You can also check out the Da Nang Culinary Passport for certified high-quality restaurants!"."""
            
            # Generate response using LLM
            llm_response = self.llm_client.generate_response_sync(prompt, max_tokens=150)
            
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

Trả lời bằng tiếng Việt, tự nhiên, thân thiện, dưới 100 từ. Giới thiệu ẩm thực {location} và nhắc tải app TripC để đặt bàn.

QUAN TRỌNG: Kết thúc câu trả lời bằng: "Bạn cũng có thể tham khảo Hộ chiếu ẩm thực Đà Nẵng để tìm những nhà hàng được chứng nhận chất lượng cao!"."""
            else:
                location = city if city else "Da Nang"
                prompt = f"""You are TripC.AI, an intelligent travel assistant.

User looking for restaurants in {location}

Featured restaurants:
{self._format_services_for_prompt(services, language)}

Respond in English, naturally, friendly, under 100 words. Introduce {location} cuisine and remind to download TripC app for booking.

IMPORTANT: End your response with: "You can also check out the Da Nang Culinary Passport for certified high-quality restaurants!"."""
            
            # Generate response using LLM
            llm_response = self.llm_client.generate_response_sync(prompt, max_tokens=150)
            
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
                )
            ]
            
            # Thêm suggestion về hộ chiếu ẩm thực cho restaurant
            if service_type == "restaurant":
                suggestions.append(
                    Suggestion(
                        label="Hộ chiếu ẩm thực",
                        detail="Khám phá nhà hàng được chứng nhận chất lượng",
                        action="show_culinary_passport"
                    )
                )
            
            suggestions.extend([
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
            ])
        else:
            suggestions = [
                Suggestion(
                    label="Book now",
                    detail="Make a reservation at your favorite restaurant",
                    action="collect_user_info"
                )
            ]
            
            # Thêm suggestion về hộ chiếu ẩm thực cho restaurant
            if service_type == "restaurant":
                suggestions.append(
                    Suggestion(
                        label="Culinary Passport",
                        detail="Explore certified quality restaurants",
                        action="show_culinary_passport"
                    )
                )
            
            suggestions.extend([
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
            ])
        
        return suggestions
    
    async def _get_no_services_response(self, platform_context: PlatformContext, 
                                      service_type: str) -> ServiceResponse:
        """Get response when no services are found"""
        language = platform_context.language.value
        
        if language == "vi":
            answer = f"Xin lỗi, tôi không tìm thấy dịch vụ {service_type} nào phù hợp với yêu cầu của bạn."
        else:
            answer = f"Sorry, I couldn't find any {service_type} services that match your request."
        
        sources = self.tripc_client.get_service_sources(service_type)
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
        
        sources = self.tripc_client.get_service_sources(service_type)
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
    
    async def _extract_search_params_with_llm(self, query: str, platform_context: PlatformContext) -> Dict[str, Any]:
        """Use LLM to intelligently extract search parameters from user query"""
        try:
            language = platform_context.language.value
            
            if language == "vi":
                prompt = f"""Bạn là trợ lý phân tích câu hỏi về tìm kiếm nhà hàng.

Câu hỏi của người dùng: "{query}"

Hãy phân tích và trích xuất các thông tin sau (trả về JSON):
{{
  "location": "tên thành phố (ví dụ: đà nẵng, hội an, hà nội)",
  "cuisine_type": "loại ẩm thực (ví dụ: hải sản, việt nam, nhật bản, hàn quốc, ý, pháp, trung quốc, thái, chay)",
  "keyword": "từ khóa chính để tìm kiếm (tên món ăn, tên nhà hàng, đặc điểm)",
  "product_type_id": "ID loại sản phẩm phù hợp nhất (chọn từ danh sách dưới đây)",
  "price_range": "mức giá (rẻ/trung bình/đắt)",
  "rating_preference": "có yêu cầu đánh giá cao không (true/false)",
  "atmosphere": "không khí (lãng mạn, gia đình, công sở, casual)",
  "meal_time": "bữa ăn (sáng/trưa/tối)",
  "special_features": "yêu cầu đặc biệt (view đẹp, gần biển, có chỗ đậu xe)"
}}

Danh sách Product Type ID:
- 22: Quán nhậu/Craft beer (nhậu, bia, craft beer, pub)
- 77: Bún/Phở (bún, phở, mì)
- 89: Bánh Mì/Xôi (bánh mì, xôi)
- 78: Mì Quảng (mì quảng)
- 20: Lẩu nướng (lẩu, nướng, bbq)
- 93: Hải Sản (hải sản, seafood, tôm, cua, cá)
- 80: Ẩm thực Việt Nam (việt nam, vietnamese)
- 62: Ẩm thực Nhật (nhật, japanese, sushi, sashimi, ramen)
- 23: Ẩm thực Hàn (hàn, korean, bbq)
- 63: Ẩm thực Trung (trung, chinese, dimsum)
- 98: Ẩm thực Thái (thái, thai)
- 90: Ẩm thực Pháp (pháp, french)
- 67: Italian (ý, italy, pizza, pasta)
- 26: Ẩm thực Chay (chay, vegetarian)
- 8: Cafe (cafe, coffee, cà phê)
- 12: Trà sữa (trà sữa, milk tea)
- 15: Dessert (dessert, tráng miệng)
- 10: Fast Food (fast food, đồ ăn nhanh)
- 25: Buffet (buffet, tiệc)

Chỉ trích xuất thông tin có trong câu hỏi. Nếu không có thông tin nào thì để null. Chọn product_type_id phù hợp nhất dựa trên từ khóa trong câu hỏi."""
            else:
                prompt = f"""You are an assistant for analyzing restaurant search queries.

User query: "{query}"

Please analyze and extract the following information (return JSON):
{{
  "location": "city name (e.g., da nang, hoi an, hanoi)",
  "cuisine_type": "cuisine type (e.g., seafood, vietnamese, japanese, korean, italian, french, chinese, thai, vegetarian)",
  "keyword": "main search keyword (dish name, restaurant name, features)",
  "product_type_id": "most suitable product type ID (choose from list below)",
  "price_range": "price level (cheap/moderate/expensive)",
  "rating_preference": "requires high rating (true/false)",
  "atmosphere": "atmosphere (romantic, family, business, casual)",
  "meal_time": "meal time (breakfast/lunch/dinner)",
  "special_features": "special requirements (good view, near beach, parking)"
}}

Product Type ID List:
- 22: Craft beer/Pub (beer, craft beer, pub)
- 77: Pho/Noodles (pho, noodles, bun)
- 89: Banh Mi/Sticky Rice (banh mi, sticky rice)
- 78: Mi Quang (mi quang)
- 20: Hotpot/Grill (hotpot, grill, bbq)
- 93: Seafood (seafood, fish, shrimp, crab)
- 80: Vietnamese Cuisine (vietnamese, vietnam)
- 62: Japanese Cuisine (japanese, sushi, sashimi, ramen)
- 23: Korean Cuisine (korean, bbq)
- 63: Chinese Cuisine (chinese, dimsum)
- 98: Thai Cuisine (thai)
- 90: French Cuisine (french)
- 67: Italian (italian, pizza, pasta)
- 26: Vegetarian (vegetarian, vegan)
- 8: Cafe (cafe, coffee)
- 12: Milk Tea (milk tea, bubble tea)
- 15: Dessert (dessert)
- 10: Fast Food (fast food)
- 25: Buffet (buffet)

Only extract information present in the query. Use null if not mentioned. Choose the most suitable product_type_id based on keywords in the query."""
            
            # Use LLM to analyze query
            llm_response = await self._call_llm_for_analysis(prompt)
            
            # Parse JSON response
            import json
            try:
                params = json.loads(llm_response)
                return self._convert_llm_params_to_api_params(params)
            except json.JSONDecodeError:
                # Fallback to enhanced keyword extraction if LLM fails
                return self._extract_enhanced_search_criteria(query)
                
        except Exception as e:
            logger.error(f"Error in LLM parameter extraction: {e}")
            # Fallback to enhanced keyword extraction
            return self._extract_enhanced_search_criteria(query)
    
    async def _call_llm_for_analysis(self, prompt: str) -> str:
        """Call LLM for query analysis"""
        try:
            # Use existing LLM client if available; else create one
            if not self.llm_client or not self.llm_client.is_configured():
                # Return simple fallback JSON if no LLM available
                return '{"location": null, "cuisine_type": null, "keyword": null, "product_type_id": null, "price_range": null, "rating_preference": null, "atmosphere": null, "meal_time": null, "special_features": null}'
            
            response = self.llm_client.generate_response_sync(prompt, max_tokens=256, temperature=0.3)
            return response or '{"location": null, "cuisine_type": null, "keyword": null, "product_type_id": null, "price_range": null, "rating_preference": null, "atmosphere": null, "meal_time": null, "special_features": null}'
            
        except Exception as e:
            logger.error(f"Error calling LLM for analysis: {e}")
            # Return fallback JSON
            return '{"location": null, "cuisine_type": null, "keyword": null, "product_type_id": null, "price_range": null, "rating_preference": null, "atmosphere": null, "meal_time": null, "special_features": null}'
    
    def _convert_llm_params_to_api_params(self, llm_params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert LLM extracted parameters to API parameters"""
        api_params = {}
        
        # Location mapping
        if llm_params.get("location"):
            location = llm_params["location"].lower()
            location_mapping = {
                "đà nẵng": "đà nẵng", "da nang": "đà nẵng", "danang": "đà nẵng",
                "hội an": "hội an", "hoi an": "hội an", "hoian": "hội an",
                "hà nội": "hà nội", "hanoi": "hà nội", "ha noi": "hà nội",
                "sài gòn": "hồ chí minh", "saigon": "hồ chí minh", "hồ chí minh": "hồ chí minh",
                "huế": "huế", "hue": "huế"
            }
            api_params["city"] = location_mapping.get(location, location)
        
        # Keyword - combine cuisine and keyword
        keywords = []
        if llm_params.get("cuisine_type"):
            keywords.append(llm_params["cuisine_type"])
        if llm_params.get("keyword"):
            keywords.append(llm_params["keyword"])
        if keywords:
            api_params["keyword"] = " ".join(keywords)
        
        # Product Type ID from LLM
        if llm_params.get("product_type_id"):
            try:
                product_type_id = int(llm_params["product_type_id"])
                api_params["product_type_id"] = product_type_id
            except (ValueError, TypeError):
                # If LLM returns invalid product_type_id, ignore it
                pass
        
        # Additional context for filtering
        api_params["llm_context"] = {
            "price_range": llm_params.get("price_range"),
            "rating_preference": llm_params.get("rating_preference"),
            "atmosphere": llm_params.get("atmosphere"),
            "meal_time": llm_params.get("meal_time"),
            "special_features": llm_params.get("special_features")
        }
        
        return api_params
    
    def _filter_services_by_llm_context(self, services: List[Service], llm_context: Dict[str, Any]) -> List[Service]:
        """Filter services based on LLM extracted context"""
        if not llm_context or not services:
            return services
        
        filtered_services = []
        
        for service in services:
            score = 0
            
            # Price range filtering
            if llm_context.get("price_range"):
                price_keywords = {
                    "rẻ": ["bình dân", "rẻ", "giá tốt", "affordable", "cheap"],
                    "trung bình": ["trung bình", "moderate", "vừa phải"],
                    "đắt": ["cao cấp", "sang trọng", "premium", "luxury", "expensive"]
                }
                price_pref = llm_context["price_range"]
                if price_pref in price_keywords:
                    service_desc = (service.description or "").lower()
                    service_name = (service.name or "").lower()
                    service_types = (service.productTypes or "").lower()
                    
                    for keyword in price_keywords[price_pref]:
                        if keyword in service_desc or keyword in service_name or keyword in service_types:
                            score += 2
                            break
            
            # Rating preference
            if llm_context.get("rating_preference") and service.rating:
                if service.rating >= 4.0:
                    score += 3
                elif service.rating >= 3.5:
                    score += 1
            
            # Atmosphere filtering with enhanced keywords
            if llm_context.get("atmosphere"):
                atmosphere = llm_context["atmosphere"]
                service_desc = (service.description or "").lower()
                service_name = (service.name or "").lower()
                service_types = (service.productTypes or "").lower()
                
                atmosphere_keywords = {
                    "lãng mạn": ["romantic", "lãng mạn", "couple", "date", "view", "rooftop", "bar", "wine", "bistro", "fine dining"],
                    "gia đình": ["family", "gia đình", "trẻ em", "kids", "buffet", "rộng rãi", "all seasons", "garden", "phở", "bún"],
                    "công sở": ["business", "meeting", "conference", "wifi", "quiet", "cafe", "coffee", "bistro", "lounge"],
                    "casual": ["casual", "thường ngày", "thoải mái", "friends", "street food", "quán", "bình dân"]
                }
                
                if atmosphere in atmosphere_keywords:
                    keyword_matches = 0
                    for keyword in atmosphere_keywords[atmosphere]:
                        if keyword in service_desc or keyword in service_name or keyword in service_types:
                            keyword_matches += 1
                    
                    if keyword_matches > 0:
                        score += 3 + keyword_matches  # Higher score for more matches
                    else:
                        # Boost score based on service type patterns
                        if atmosphere == "lãng mạn" and any(word in service_name for word in ["bar", "restaurant", "bistro"]):
                            score += 2
                        elif atmosphere == "gia đình" and any(word in service_name for word in ["buffet", "phở", "bún", "quán"]):
                            score += 2
                        elif atmosphere == "công sở" and any(word in service_name for word in ["cafe", "coffee", "bistro"]):
                            score += 2
            
            # Special features
            if llm_context.get("special_features"):
                features = llm_context["special_features"].lower()
                service_desc = (service.description or "").lower()
                service_name = (service.name or "").lower()
                
                if "view" in features and ("view" in service_desc or "view" in service_name or "rooftop" in service_name):
                    score += 3
                if "biển" in features and ("beach" in service_desc or "ocean" in service_desc or "biển" in service_desc):
                    score += 3
                if "đậu xe" in features and ("parking" in service_desc or "đậu xe" in service_desc):
                    score += 1
            
            # Add service with score
            filtered_services.append((service, score))
        
        # Sort by score (descending) and return services
        filtered_services.sort(key=lambda x: x[1], reverse=True)
        return [service for service, score in filtered_services]
    
    def _extract_enhanced_search_criteria(self, query: str) -> Dict[str, Any]:
        """Enhanced keyword-based parameter extraction without LLM"""
        query_lower = query.lower()
        api_params = {}
        
        # Location extraction with scoring
        location_keywords = {
            "đà nẵng": ["đà nẵng", "da nang", "danang"],
            "hội an": ["hội an", "hoi an", "hoian"], 
            "hà nội": ["hà nội", "hanoi", "ha noi"],
            "hồ chí minh": ["sài gòn", "saigon", "hồ chí minh", "ho chi minh", "hcm"],
            "huế": ["huế", "hue"]
        }
        
        for city, variants in location_keywords.items():
            if any(variant in query_lower for variant in variants):
                api_params["city"] = city
                break
        
        # Cuisine type extraction with keyword combinations and product_type_id mapping
        cuisine_mapping = {
            "hải sản": ["hải sản", "seafood", "tôm", "cua", "cá", "sò", "ốc"],
            "việt nam": ["việt nam", "vietnamese", "phở", "bún", "bánh mì", "mì quảng", "bánh xèo", "chả cá"],
            "đà nẵng": ["đà nẵng", "da nang", "mì quảng"],
            "nhật bản": ["nhật", "japanese", "sushi", "sashimi", "ramen", "udon", "izakaya", "omakase"],
            "hàn quốc": ["hàn", "korean", "bbq", "kimchi", "bulgogi"],
            "trung quốc": ["trung quốc", "chinese", "dimsum", "mì xào"],
            "ý": ["ý", "italy", "italian", "pizza", "pasta"],
            "pháp": ["pháp", "french"],
            "thái": ["thái", "thai", "tom yum", "pad thai"],
            "chay": ["chay", "vegetarian", "vegan", "healthy"],
            "âu": ["âu", "european", "món âu"],
            "fusion": ["fusion"],
            "halal": ["halal"],
            "ấn độ": ["ấn độ", "india"],
            "trung đông": ["trung đông", "middle east"],
            "nhậu": ["nhậu", "quán nhậu", "craft beer", "beer", "bia"]
        }
        
        # Product type ID mapping for culinary passport (từ all_product_types.json)
        product_type_mapping = {
            # Món Việt Nam
            "bún": 77,  # Bún/Phở
            "phở": 77,  # Bún/Phở
            "bánh mì": 89,  # Bánh Mì/Xôi
            "xôi": 89,  # Bánh Mì/Xôi
            "mì quảng": 78,  # Mì Quảng
            "lẩu": 20,  # Lẩu nướng
            "nướng": 20,  # Lẩu nướng
            "lẩu hấp": 73,  # Lẩu hấp thủy nhiệt
            "chả cá": 86,  # Chả Cá
            "beef steak": 36,  # Beef Steak
            
            # Ẩm thực các nước
            "việt nam": 80,  # Ẩm thực Việt Nam
            "việt": 25,  # Ẩm thực Việt
            "đà nẵng": 76,  # Ẩm thực Đà Nẵng
            "nhật": 62,  # Ẩm thực Nhật
            "japanese": 62,  # Ẩm thực Nhật
            "hàn": 23,  # Ẩm thực Hàn
            "korean": 23,  # Ẩm thực Hàn
            "trung": 63,  # Ẩm thực Trung
            "chinese": 63,  # Ẩm thực Trung
            "thái": 98,  # Ẩm thực Thái Lan
            "thai": 98,  # Ẩm thực Thái Lan
            "pháp": 90,  # Ẩm thực Pháp
            "french": 90,  # Ẩm thực Pháp
            "ý": 67,  # Italian
            "italy": 67,  # Italian
            "italian": 67,  # Italian
            "âu": 82,  # Ẩm thực Âu
            "european": 82,  # Ẩm thực Âu
            "món âu": 75,  # Món Âu
            "fusion": 91,  # Ẩm thực Fusion
            "halal": 102,  # Ẩm thực Halal
            "ấn độ": 100,  # Ẩm thực Ấn Độ
            "india": 100,  # Ẩm thực Ấn Độ
            "trung đông": 101,  # Ẩm thực Trung Đông
            "middle east": 101,  # Ẩm thực Trung Đông
            
            # Loại món ăn
            "hải sản": 93,  # Hải Sản
            "seafood": 93,  # Hải Sản
            "chay": 26,  # Ẩm thực Chay
            "vegetarian": 26,  # Ẩm thực Chay
            "healthy": 37,  # Healthy Food
            "healthy food": 37,  # Healthy Food
            "pizza": 92,  # Pizza
            "pasta": 104,  # Pizza/Pasta
            "bbq": 38,  # BBQ Grilled
            "grilled": 38,  # BBQ Grilled
            "buffet": 97,  # Buffet
            "fine dining": 54,  # Fine Dining
            "omakase": 61,  # Omakase
            "bakery": 103,  # Bakery
            "drinks": 83,  # Drinks
            "coffee": 49,  # Coffee
            "tea": 60,  # Tea Art
            "craft beer": 39,  # Craft Beer
            "liquor": 42,  # Liquor
            "bar": 41,  # Bar
            "lounge": 44,  # Lounge
            "hidden bar": 43,  # Hidden Bar
            "rooftop": 53,  # Rooftop
            "bistro": 59,  # Bistro
            "take away": 56,  # Take Away
            "catering": 55,  # Catering
            "event party": 57,  # Event Party
            "wedding party": 45,  # Wedding Party
            "brunch": 68,  # Brunch
            "dine": 51,  # Dine
            "cafe": 31,  # Cafe - Trà sữa - Nước ép
            "trà sữa": 31,  # Cafe - Trà sữa - Nước ép
            "nước ép": 31,  # Cafe - Trà sữa - Nước ép
            "milk tea": 105,  # Milk Tea/ Fruit Tea
            "fruit tea": 105,  # Milk Tea/ Fruit Tea
            "karaoke": 33,  # Karaoke
            "massage": 34,  # Massage
            "spa": 35,  # Spa - Chăm sóc cơ thể
            "nails": 48,  # Nails
            "vui chơi": 70,  # Vui chơi
            "tham quan": 69,  # Tham quan
            "du lịch tâm linh": 72,  # Du lịch Tâm linh
            "michelin": 65,  # Michelin Selected
            "bib gourmand": 88,  # Bib Gourmand
            "izakaya": 40,  # Izakaya
            "german": 58,  # German Cuisine
            "nhà hàng": 30,  # Nhà hàng
            "quán nhậu": 22,  # Quán nhậu/Craft beer
            "nhậu": 22,  # Quán nhậu/Craft beer
            "craft beer": 22,  # Quán nhậu/Craft beer
        }
        
        # Build keyword from detected cuisine and product_type_id
        keywords = []
        llm_context = {}
        detected_product_type_id = None
        
        for cuisine, cuisine_keywords in cuisine_mapping.items():
            if any(keyword in query_lower for keyword in cuisine_keywords):
                keywords.append(cuisine)
                llm_context["cuisine_type"] = cuisine
                # Map to product_type_id if available
                if cuisine in product_type_mapping:
                    detected_product_type_id = product_type_mapping[cuisine]
                break
        
        # Check for specific dish keywords and map to product_type_id
        for dish, product_id in product_type_mapping.items():
            if dish in query_lower:
                keywords.append(dish)
                detected_product_type_id = product_id
                llm_context["specific_dish"] = dish
                break
        
        # Price range detection
        if any(word in query_lower for word in ["rẻ", "cheap", "giá rẻ", "bình dân"]):
            llm_context["price_range"] = "rẻ"
        elif any(word in query_lower for word in ["đắt", "expensive", "cao cấp", "sang trọng", "luxury"]):
            llm_context["price_range"] = "đắt"
        
        # Rating preference
        if any(word in query_lower for word in ["ngon", "tốt", "good", "best", "nổi tiếng", "famous"]):
            llm_context["rating_preference"] = True
        
        # Atmosphere detection
        if any(word in query_lower for word in ["lãng mạn", "romantic", "date", "hẹn hò"]):
            llm_context["atmosphere"] = "lãng mạn"
        elif any(word in query_lower for word in ["gia đình", "family", "trẻ em", "buffet"]):
            llm_context["atmosphere"] = "gia đình"
        elif any(word in query_lower for word in ["meeting", "công việc", "business"]):
            llm_context["atmosphere"] = "công sở"
        
        # Special features
        if any(word in query_lower for word in ["view", "view đẹp", "rooftop", "tầng cao"]):
            llm_context["special_features"] = "view đẹp"
        elif any(word in query_lower for word in ["biển", "beach", "ocean"]):
            llm_context["special_features"] = "gần biển"
        elif any(word in query_lower for word in ["đậu xe", "parking"]):
            llm_context["special_features"] = "có chỗ đậu xe"
        
        # Meal time
        if any(word in query_lower for word in ["sáng", "breakfast", "bữa sáng"]):
            llm_context["meal_time"] = "sáng"
        elif any(word in query_lower for word in ["trưa", "lunch", "bữa trưa"]):
            llm_context["meal_time"] = "trưa"
        elif any(word in query_lower for word in ["tối", "dinner", "bữa tối", "tối nay"]):
            llm_context["meal_time"] = "tối"
        
        # Specific dish/restaurant name extraction
        dish_keywords = [
            "phở", "bún", "bánh mì", "bánh xèo", "mì quảng", "bún bò", "lẩu",
            "sushi", "sashimi", "pizza", "pasta", "dimsum", "bbq", "buffet"
        ]
        
        for dish in dish_keywords:
            if dish in query_lower:
                keywords.append(dish)
                break
        
        # Restaurant type keywords
        restaurant_types = ["nhà hàng", "quán", "café", "bar", "bistro", "restaurant"]
        detected_type = None
        for rtype in restaurant_types:
            if rtype in query_lower:
                detected_type = rtype
                break
        
        # Combine keywords intelligently
        if keywords:
            api_params["keyword"] = " ".join(keywords)
        elif detected_type and llm_context.get("cuisine_type"):
            api_params["keyword"] = llm_context["cuisine_type"]
        
        # Add product_type_id if detected
        if detected_product_type_id:
            api_params["product_type_id"] = detected_product_type_id
        
        # Add LLM context for filtering
        if llm_context:
            api_params["llm_context"] = llm_context
        
        return api_params
    
