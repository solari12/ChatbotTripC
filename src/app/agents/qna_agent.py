#qna_agent.py
from typing import List, Optional, Dict, Any
from ..models.schemas import QnAResponse, Source, Suggestion
from ..vector.pgvector_store import get_embedding, embedding_to_pgvector_str, search_similar, ask_llm
from ..core.platform_context import PlatformContext
from ..llm.rate_limited_client import RateLimitedLLMClient
import logging

logger = logging.getLogger(__name__)


class QnAAgent:
    """QnA Agent using vector embedding search with LLM for natural responses"""
    
    def __init__(self, vector_store, llm_client: RateLimitedLLMClient = None):
        self.vector_store = vector_store
        self.llm_client = llm_client
        if llm_client is None:
            from ..llm.open_client import OpenAIClient
            base_llm_client = OpenAIClient()
            self.llm_client = RateLimitedLLMClient(base_llm_client)
        
        # Pre-defined QnA content for common queries
        self.common_responses = {
            "vi": {
                "greeting": "Xin chào! Tôi là TripC.AI, trợ lý du lịch thông minh. Tôi có thể giúp bạn tìm nhà hàng, địa điểm du lịch và đặt chỗ tại Đà Nẵng, Hội An và các thành phố khác.",
                "help": "Tôi có thể giúp bạn:\n• Tìm nhà hàng và đặt bàn\n• Khám phá địa điểm du lịch\n• Tư vấn về ẩm thực và văn hóa\n• Hỗ trợ đặt chỗ và dịch vụ"
            },
            "en": {
                "greeting": "Hello! I'm TripC.AI, your smart travel assistant. I can help you find restaurants, tourist attractions, and make bookings in Da Nang, Hoi An, and other cities.",
                "help": "I can help you with:\n• Finding restaurants and making reservations\n• Discovering tourist attractions\n• Food and culture advice\n• Booking support and services"
            }
        }
    
    async def search_embedding(self, query: str, platform_context: PlatformContext, 
                             top_k: int = 5) -> QnAResponse:
        """Search for QnA content using vector similarity and LLM for natural responses"""
        try:
            
            emb = get_embedding(query)
            emb_str = embedding_to_pgvector_str(emb)
            results = search_similar(emb_str)
            contexts = [row[2] for row in results]
            answer_ai = ask_llm(query, contexts)
            
            # Create sources from search results
            sources = [
                Source(
                    title=result.get("metadata", {}).get("title", "TripC Travel Guide"),
                    url=result.get("metadata", {}).get("url", "https://tripc.ai"),
                    imageUrl=result.get("metadata", {}).get("imageUrl")
                )
                for result in results[:3]  # Top 3 sources
            ]
            
            # Generate contextual suggestions
            suggestions = await self._generate_llm_suggestions(query, results, platform_context)
            
            return QnAResponse(
                type="QnA",
                answerAI=answer_ai,
                sources=sources,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error in QnA search: {e}")
            return await self._get_fallback_response(query, platform_context)
    
    async def _generate_llm_suggestions(self, query: str, results: List[Dict[str, Any]], 
                                      platform_context: PlatformContext) -> List[Suggestion]:
        """Generate contextual suggestions using LLM with platform-aware strategy"""
        
        try:
            language = platform_context.language.value
            platform = platform_context.platform.value
            device = platform_context.device.value
            
            if language == "vi":
                prompt = f"""Dựa trên câu hỏi: "{query}", hãy đề xuất 3 hành động hữu ích và liên quan mà người dùng có thể thực hiện tiếp theo.

Yêu cầu BẮT BUỘC:
1. Suggestions phải liên quan trực tiếp đến nội dung câu hỏi
2. Nếu hỏi về nhà hàng → đề xuất tìm nhà hàng, đặt bàn, xem menu
3. Nếu hỏi về địa điểm → đề xuất khám phá địa điểm, tìm hiểu thêm, đặt tour
4. Nếu hỏi về văn hóa → đề xuất tìm hiểu văn hóa, tham quan, trải nghiệm
5. Nếu hỏi chung chung → đề xuất các dịch vụ chính

QUY TẮC PLATFORM (BẮT BUỘC TUÂN THEO):
- Platform: {platform}, Device: {device}
- Nếu web_browser: PHẢI có ít nhất 1 suggestion với action="download_app"
- Nếu mobile_app: PHẢI có ít nhất 1 suggestion với action="collect_user_info"

Ví dụ cho web_browser:
- Nếu hỏi nhà hàng: [show_services, show_services, download_app]
- Nếu hỏi địa điểm: [show_attractions, show_attractions, download_app]

Ví dụ cho mobile_app:
- Nếu hỏi nhà hàng: [show_services, show_services, collect_user_info]
- Nếu hỏi địa điểm: [show_attractions, show_attractions, collect_user_info]

Trả về chính xác và nhanh nhất có thể theo format JSON này (không có text thêm):
[
    {{"label": "Tên suggestion", "detail": "Mô tả chi tiết", "action": "show_services|show_attractions|collect_user_info|show_culture|download_app"}}
]"""
            else:
                prompt = f"""Based on the question: "{query}", suggest 3 useful and relevant actions the user can take next.

MANDATORY Requirements:
1. Suggestions must be directly related to the question content
2. If asking about restaurants → suggest finding restaurants, making reservations, viewing menus
3. If asking about attractions → suggest exploring places, learning more, booking tours
4. If asking about culture → suggest learning about culture, visiting sites, experiencing
5. If asking generally → suggest main services

PLATFORM RULES (MUST FOLLOW):
- Platform: {platform}, Device: {device}
- If web_browser: MUST include at least 1 suggestion with action="download_app"
- If mobile_app: MUST include at least 1 suggestion with action="collect_user_info"

Examples for web_browser:
- If asking about restaurants: [show_services, show_services, download_app]
- If asking about attractions: [show_attractions, show_attractions, download_app]

Examples for mobile_app:
- If asking about restaurants: [show_services, show_services, collect_user_info]
- If asking about attractions: [show_attractions, show_attractions, collect_user_info]

Return exactly in this JSON format (no additional text):
[
    {{"label": "Suggestion name", "detail": "Detailed description", "action": "show_services|show_attractions|collect_user_info|show_culture|download_app"}}
]"""
            
            # Use ask_llm for suggestions instead of self.llm_client
            response = ask_llm(f"Suggestions: {prompt}", [prompt])
            
            if response:
                try:
                    import json
                    import re
                    
                    # Clean the response to extract JSON
                    cleaned_response = response.strip()
                    
                    # Try to find JSON array in the response
                    json_match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        suggestions_data = json.loads(json_str)
                        
                        # Validate and create suggestions
                        valid_suggestions = []
                        for s in suggestions_data[:3]:
                            if isinstance(s, dict) and s.get("label") and s.get("action"):
                                # Validate action type
                                action = s.get("action", "show_services")
                                if action not in ["show_services", "show_attractions", "collect_user_info", "show_culture", "download_app"]:
                                    action = "show_services"  # Default fallback
                                
                                valid_suggestions.append(
                                    Suggestion(
                                        label=s.get("label", ""),
                                        detail=s.get("detail"),
                                        action=action
                                    )
                                )
                        
                        if valid_suggestions:
                            return valid_suggestions
                    
                    # If JSON parsing fails, try to extract suggestions from text
                    logger.warning("JSON parsing failed, attempting text extraction")
                    return self._extract_suggestions_from_text(response, platform_context)
                    
                except (json.JSONDecodeError, KeyError, AttributeError) as e:
                    logger.warning(f"Failed to parse LLM suggestions: {e}, using defaults")
                    return self._get_default_suggestions(platform_context)
            else:
                return self._get_default_suggestions(platform_context)
                
        except Exception as e:
            logger.error(f"Error generating LLM suggestions: {e}")
            return self._get_default_suggestions(platform_context)
    
    def _extract_suggestions_from_text(self, text: str, platform_context: PlatformContext) -> List[Suggestion]:
        """Extract suggestions from LLM text response when JSON parsing fails"""
        try:
            language = platform_context.language.value
            
            # Try to extract meaningful suggestions from text
            lines = text.strip().split('\n')
            suggestions = []
            
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:  # Skip empty or very short lines
                    # Try to identify suggestion patterns
                    if any(keyword in line.lower() for keyword in ['nhà hàng', 'restaurant', 'địa điểm', 'attraction', 'đặt', 'book']):
                        if language == "vi":
                            suggestions.append(Suggestion(
                                label=line[:30] + "..." if len(line) > 30 else line,
                                detail=line,
                                action="show_services"
                            ))
                        else:
                            suggestions.append(Suggestion(
                                label=line[:30] + "..." if len(line) > 30 else line,
                                detail=line,
                                action="show_services"
                            ))
                    
                    if len(suggestions) >= 3:
                        break
            
            # If we found some suggestions, return them
            if suggestions:
                return suggestions
            
        except Exception as e:
            logger.warning(f"Error extracting suggestions from text: {e}")
        
        # Fallback to defaults
        return self._get_default_suggestions(platform_context)
    
    def _get_default_suggestions(self, platform_context: PlatformContext) -> List[Suggestion]:
        """Get default suggestions when LLM is not available - platform-aware"""
        language = platform_context.language.value
        platform = platform_context.platform.value
        
        if language == "vi":
            if platform == "web_browser":
                return [
                    Suggestion(
                        label="Tìm nhà hàng gần đây",
                        detail="Khám phá các nhà hàng nổi tiếng tại Đà Nẵng",
                        action="show_services"
                    ),
                    Suggestion(
                        label="Địa điểm du lịch",
                        detail="Tìm hiểu về các điểm đến hấp dẫn",
                        action="show_attractions"
                    ),
                    Suggestion(
                        label="Tải app TripC",
                        detail="Tải app để xem chi tiết và đặt chỗ dễ dàng",
                        action="download_app"
                    )
                ]
            else:  # mobile_app
                return [
                    Suggestion(
                        label="Tìm nhà hàng gần đây",
                        detail="Khám phá các nhà hàng nổi tiếng tại Đà Nẵng",
                        action="show_services"
                    ),
                    Suggestion(
                        label="Địa điểm du lịch",
                        detail="Tìm hiểu về các điểm đến hấp dẫn",
                        action="show_attractions"
                    ),
                    Suggestion(
                        label="Đặt chỗ ngay",
                        detail="Đặt bàn tại nhà hàng yêu thích",
                        action="collect_user_info"
                    )
                ]
        else:  # English
            if platform == "web_browser":
                return [
                    Suggestion(
                        label="Find nearby restaurants",
                        detail="Discover famous restaurants in Da Nang",
                        action="show_services"
                    ),
                    Suggestion(
                        label="Tourist attractions",
                        detail="Learn about exciting destinations",
                        action="show_attractions"
                    ),
                    Suggestion(
                        label="Download TripC App",
                        detail="Download the app to view details and make bookings easily",
                        action="download_app"
                    )
                ]
            else:  # mobile_app
                return [
                    Suggestion(
                        label="Find nearby restaurants",
                        detail="Discover famous restaurants in Da Nang",
                        action="show_services"
                    ),
                    Suggestion(
                        label="Tourist attractions",
                        detail="Learn about exciting destinations",
                        action="show_attractions"
                    ),
                    Suggestion(
                        label="Book now",
                        detail="Make a reservation at your favorite restaurant",
                        action="collect_user_info"
                    )
                ]
    
    async def _get_fallback_response(self, query: str, platform_context: PlatformContext) -> QnAResponse:
        """Get fallback response when vector search fails"""
        language = platform_context.language.value
        
        # Check for common query patterns
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["xin chào", "hello", "hi", "chào"]):
            answer = self.common_responses[language]["greeting"]
        elif any(word in query_lower for word in ["giúp", "help", "hỗ trợ"]):
            answer = self.common_responses[language]["help"]
        else:
            answer = "Xin lỗi, tôi không hiểu câu hỏi của bạn. Bạn có thể hỏi về nhà hàng, địa điểm du lịch hoặc đặt chỗ."
            if language == "en":
                answer = "Sorry, I don't understand your question. You can ask about restaurants, tourist attractions, or make bookings."
        
        # Create fallback sources
        sources = [
            Source(
                title="TripC Travel Guide",
                url="https://tripc.ai",
                imageUrl="https://cdn.tripc.ai/sources/tripc-guide.jpg"
            )
        ]
        
        suggestions = self._get_default_suggestions(platform_context)
        
        return QnAResponse(
            type="QnA",
            answerAI=answer,
            sources=sources,
            suggestions=suggestions
        )
    