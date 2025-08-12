from typing import List, Optional, Dict, Any
from ..models.schemas import QnAResponse, Source, Suggestion
from ..vector.pgvector_store import PgVectorStore
from ..core.platform_context import PlatformContext
import logging

logger = logging.getLogger(__name__)


class QnAAgent:
    """QnA Agent using vector embedding search with pre-indexed content"""
    
    def __init__(self, vector_store: PgVectorStore):
        self.vector_store = vector_store
        
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
        """Search for QnA content using vector similarity"""
        try:
            # Search vector store for similar content
            results = await self.vector_store.search_similarity(query, top_k=top_k)
            
            if not results:
                # Fallback to common responses
                return await self._get_fallback_response(query, platform_context)
            
            # Process search results
            answer_ai = self._format_answer(query, results)
            sources = self._extract_sources(results)
            suggestions = self._generate_suggestions(platform_context)
            
            return QnAResponse(
                type="QnA",
                answerAI=answer_ai,
                sources=sources,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error in QnA search: {e}")
            return await self._get_fallback_response(query, platform_context)
    
    def _format_answer(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Format search results into a coherent answer"""
        if not results:
            return "Xin lỗi, tôi không tìm thấy thông tin phù hợp cho câu hỏi của bạn."
        
        # Use the most relevant result as the main answer
        best_result = results[0]
        answer = best_result.get("content", "")
        
        # Add additional context from other results if available
        if len(results) > 1:
            additional_info = []
            for result in results[1:3]:  # Use top 2 additional results
                content = result.get("content", "")
                if content and len(content) > 50:  # Only add substantial content
                    additional_info.append(content[:200] + "...")
            
            if additional_info:
                answer += "\n\nThêm thông tin:\n" + "\n".join(additional_info)
        
        return answer
    
    def _extract_sources(self, results: List[Dict[str, Any]]) -> List[Source]:
        """Extract sources from search results"""
        sources = []
        
        for result in results:
            # Extract source information from embedding data
            source_data = result.get("metadata", {})
            
            source = Source(
                title=source_data.get("title", "TripC Travel Guide"),
                url=source_data.get("url", "https://tripc.ai"),
                imageUrl=source_data.get("imageUrl")  # From pre-indexed embedding data
            )
            sources.append(source)
        
        return sources
    
    def _generate_suggestions(self, platform_context: PlatformContext) -> List[Suggestion]:
        """Generate platform-aware suggestions"""
        suggestions = [
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
        
        # Localize suggestions based on language
        if platform_context.language.value == "en":
            suggestions = [
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
        
        return suggestions
    
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
        
        suggestions = self._generate_suggestions(platform_context)
        
        return QnAResponse(
            type="QnA",
            answerAI=answer,
            sources=sources,
            suggestions=suggestions
        )
    
    async def get_restaurant_recommendations(self, platform_context: PlatformContext) -> QnAResponse:
        """Get restaurant recommendations for QnA context"""
        answer = "Dưới đây là những nhà hàng tuyệt vời tại Đà Nẵng mà bạn nên thử:"
        if platform_context.language.value == "en":
            answer = "Here are some great restaurants in Da Nang that you should try:"
        
        sources = [
            Source(
                title="TripC Restaurant Guide - Đà Nẵng",
                url="https://tripc.ai/danang-restaurants",
                imageUrl="https://cdn.tripc.ai/sources/restaurant-guide.jpg"
            )
        ]
        
        suggestions = [
            Suggestion(
                label="Xem danh sách nhà hàng",
                detail="Khám phá tất cả nhà hàng có sẵn",
                action="show_services"
            ),
            Suggestion(
                label="Đặt bàn ngay",
                detail="Đặt chỗ tại nhà hàng yêu thích",
                action="collect_user_info"
            )
        ]
        
        if platform_context.language.value == "en":
            suggestions = [
                Suggestion(
                    label="View restaurant list",
                    detail="Explore all available restaurants",
                    action="show_services"
                ),
                Suggestion(
                    label="Book now",
                    detail="Make a reservation at your favorite restaurant",
                    action="collect_user_info"
                )
            ]
        
        return QnAResponse(
            type="QnA",
            answerAI=answer,
            sources=sources,
            suggestions=suggestions
        )