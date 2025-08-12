import asyncio
from typing import List, Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


class PgVectorStore:
    """PgVector store for embedding search with pre-indexed content"""
    
    def __init__(self):
        # For now, we'll use a mock implementation
        # In production, this would connect to PostgreSQL with pgvector extension
        self.initialized = False
        self.mock_data = self._initialize_mock_data()
    
    def _initialize_mock_data(self) -> List[Dict[str, Any]]:
        """Initialize mock embedding data for development"""
        return [
            {
                "id": 1,
                "content": "Đà Nẵng là thành phố biển xinh đẹp với những bãi biển dài, cát trắng mịn và nước biển trong xanh. Bãi biển Mỹ Khê được bình chọn là một trong những bãi biển đẹp nhất thế giới.",
                "metadata": {
                    "title": "Du lịch Đà Nẵng - Hướng dẫn chi tiết",
                    "url": "https://tripc.ai/danang-guide",
                    "imageUrl": "https://cdn.tripc.ai/sources/danang-guide.jpg",
                    "category": "travel_guide",
                    "city": "danang"
                },
                "embedding": [0.1, 0.2, 0.3]  # Mock embedding vector
            },
            {
                "id": 2,
                "content": "Hội An là thành phố cổ với kiến trúc truyền thống Việt Nam được bảo tồn nguyên vẹn. Phố cổ Hội An được UNESCO công nhận là Di sản Văn hóa Thế giới.",
                "metadata": {
                    "title": "Khám phá Hội An - Thành phố cổ",
                    "url": "https://tripc.ai/hoian-guide",
                    "imageUrl": "https://cdn.tripc.ai/sources/hoian-guide.jpg",
                    "category": "travel_guide",
                    "city": "hoian"
                },
                "embedding": [0.2, 0.3, 0.4]
            },
            {
                "id": 3,
                "content": "Ẩm thực Đà Nẵng nổi tiếng với món bánh mì, bánh xèo, bún chả cá và các món hải sản tươi ngon. Đặc biệt là món bánh mì Đà Nẵng với nhân thịt nướng và rau sống.",
                "metadata": {
                    "title": "Ẩm thực Đà Nẵng - Hương vị miền Trung",
                    "url": "https://tripc.ai/danang-food",
                    "imageUrl": "https://cdn.tripc.ai/sources/danang-food.jpg",
                    "category": "food_culture",
                    "city": "danang"
                },
                "embedding": [0.3, 0.4, 0.5]
            },
            {
                "id": 4,
                "content": "Bán đảo Sơn Trà là điểm du lịch nổi tiếng tại Đà Nẵng với tượng Phật Bà Quan Âm cao 67m. Từ đây bạn có thể ngắm toàn cảnh thành phố Đà Nẵng và biển Đông.",
                "metadata": {
                    "title": "Bán đảo Sơn Trà - Điểm đến không thể bỏ qua",
                    "url": "https://tripc.ai/son-tra",
                    "imageUrl": "https://cdn.tripc.ai/sources/son-tra.jpg",
                    "category": "attraction",
                    "city": "danang"
                },
                "embedding": [0.4, 0.5, 0.6]
            },
            {
                "id": 5,
                "content": "Ngũ Hành Sơn là quần thể 5 ngọn núi đá vôi nổi tiếng tại Đà Nẵng. Mỗi ngọn núi đại diện cho một yếu tố ngũ hành: Kim, Mộc, Thủy, Hỏa, Thổ.",
                "metadata": {
                    "title": "Ngũ Hành Sơn - Di tích lịch sử văn hóa",
                    "url": "https://tripc.ai/ngu-hanh-son",
                    "imageUrl": "https://cdn.tripc.ai/sources/ngu-hanh-son.jpg",
                    "category": "attraction",
                    "city": "danang"
                },
                "embedding": [0.5, 0.6, 0.7]
            }
        ]
    
    async def initialize(self):
        """Initialize the vector store"""
        try:
            # In production, this would establish database connection
            # For now, just mark as initialized
            self.initialized = True
            logger.info("PgVector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PgVector store: {e}")
            raise
    
    async def search_similarity(self, query: str, top_k: int = 5, 
                              threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar content using vector similarity"""
        try:
            if not self.initialized:
                await self.initialize()
            
            # Mock similarity search
            # In production, this would use actual vector similarity search
            results = []
            
            # Simple keyword matching for mock implementation
            query_lower = query.lower()
            
            for item in self.mock_data:
                content_lower = item["content"].lower()
                metadata_lower = str(item["metadata"]).lower()
                
                # Calculate simple relevance score
                relevance_score = 0
                if query_lower in content_lower:
                    relevance_score += 0.8
                if query_lower in metadata_lower:
                    relevance_score += 0.6
                
                # Check for partial matches
                query_words = query_lower.split()
                for word in query_words:
                    if word in content_lower:
                        relevance_score += 0.3
                    if word in metadata_lower:
                        relevance_score += 0.2
                
                if relevance_score > 0:
                    results.append({
                        **item,
                        "relevance_score": relevance_score
                    })
            
            # Sort by relevance score and return top_k results
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
    
    async def add_embedding(self, content: str, metadata: Dict[str, Any], 
                           embedding: List[float]) -> bool:
        """Add new embedding to the store"""
        try:
            if not self.initialized:
                await self.initialize()
            
            # In production, this would insert into database
            # For mock implementation, add to mock_data
            new_id = max(item["id"] for item in self.mock_data) + 1
            
            new_item = {
                "id": new_id,
                "content": content,
                "metadata": metadata,
                "embedding": embedding
            }
            
            self.mock_data.append(new_item)
            logger.info(f"Added new embedding with ID: {new_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding embedding: {e}")
            return False
    
    async def update_embedding(self, embedding_id: int, content: str = None, 
                             metadata: Dict[str, Any] = None, 
                             embedding: List[float] = None) -> bool:
        """Update existing embedding"""
        try:
            if not self.initialized:
                await self.initialize()
            
            # Find and update the embedding
            for item in self.mock_data:
                if item["id"] == embedding_id:
                    if content:
                        item["content"] = content
                    if metadata:
                        item["metadata"].update(metadata)
                    if embedding:
                        item["embedding"] = embedding
                    
                    logger.info(f"Updated embedding with ID: {embedding_id}")
                    return True
            
            logger.warning(f"Embedding with ID {embedding_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error updating embedding: {e}")
            return False
    
    async def delete_embedding(self, embedding_id: int) -> bool:
        """Delete embedding by ID"""
        try:
            if not self.initialized:
                await self.initialize()
            
            # Find and remove the embedding
            for i, item in enumerate(self.mock_data):
                if item["id"] == embedding_id:
                    del self.mock_data[i]
                    logger.info(f"Deleted embedding with ID: {embedding_id}")
                    return True
            
            logger.warning(f"Embedding with ID {embedding_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting embedding: {e}")
            return False
    
    async def get_embedding_by_id(self, embedding_id: int) -> Optional[Dict[str, Any]]:
        """Get embedding by ID"""
        try:
            if not self.initialized:
                await self.initialize()
            
            for item in self.mock_data:
                if item["id"] == embedding_id:
                    return item
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting embedding by ID: {e}")
            return None
    
    async def get_embeddings_by_category(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get embeddings by category"""
        try:
            if not self.initialized:
                await self.initialize()
            
            results = []
            for item in self.mock_data:
                if item["metadata"].get("category") == category:
                    results.append(item)
                    if len(results) >= limit:
                        break
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting embeddings by category: {e}")
            return []
    
    async def get_embeddings_by_city(self, city: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get embeddings by city"""
        try:
            if not self.initialized:
                await self.initialize()
            
            results = []
            for item in self.mock_data:
                if item["metadata"].get("city") == city:
                    results.append(item)
                    if len(results) >= limit:
                        break
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting embeddings by city: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        try:
            categories = {}
            cities = {}
            
            for item in self.mock_data:
                category = item["metadata"].get("category", "unknown")
                city = item["metadata"].get("city", "unknown")
                
                categories[category] = categories.get(category, 0) + 1
                cities[city] = cities.get(city, 0) + 1
            
            return {
                "total_embeddings": len(self.mock_data),
                "categories": categories,
                "cities": cities,
                "initialized": self.initialized
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}