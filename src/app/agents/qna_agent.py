#qna_agent.py
from typing import List, Optional, Dict, Any
from ..models.schemas import QnAResponse, Source, Suggestion
from ..vector.pgvector_store import get_embedding, embedding_to_pgvector_str, search_similar, ask_llm
from ..core.platform_context import PlatformContext
from ..llm.open_client import OpenAIClient
import logging

logger = logging.getLogger(__name__)


class QnAAgent:
    """QnA Agent using vector embedding search with LLM for natural responses"""
    
    def __init__(self, llm_client: OpenAIClient = None):
        self.llm_client = llm_client or OpenAIClient()
        
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
        """Generate contextual suggestions using LLM"""
        
        try:
            language = platform_context.language.value
            
            if language == "vi":
                prompt = f"""Dựa trên câu hỏi: "{query}", hãy đề xuất 3 hành động hữu ích mà người dùng có thể thực hiện tiếp theo.
                
                Trả về chính xác theo format JSON này (không có text thêm):
                [
                    {{"label": "Tìm nhà hàng", "detail": "Khám phá các nhà hàng nổi tiếng", "action": "show_services"}},
                    {{"label": "Địa điểm du lịch", "detail": "Tìm hiểu về các điểm đến hấp dẫn", "action": "show_attractions"}},
                    {{"label": "Đặt chỗ ngay", "detail": "Đặt bàn tại nhà hàng yêu thích", "action": "collect_user_info"}}
                ]"""
            else:
                prompt = f"""Based on the question: "{query}", suggest 3 useful actions the user can take next.
                
                Return exactly in this JSON format (no additional text):
                [
                    {{"label": "Find restaurants", "detail": "Discover famous restaurants", "action": "show_services"}},
                    {{"label": "Tourist attractions", "detail": "Learn about exciting destinations", "action": "show_attractions"}},
                    {{"label": "Book now", "detail": "Make a reservation at your favorite restaurant", "action": "collect_user_info"}}
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
                                valid_suggestions.append(
                                    Suggestion(
                                        label=s.get("label", ""),
                                        detail=s.get("detail"),
                                        action=s.get("action", "show_services")
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
        """Get default suggestions when LLM is not available"""
        language = platform_context.language.value
        
        if language == "vi":
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
        else:
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
    