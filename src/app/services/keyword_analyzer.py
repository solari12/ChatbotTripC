import json
import logging
from typing import Dict, List, Optional, Any
from ..llm.open_client import OpenAIClient
from .tripc_api import TripCAPIClient

logger = logging.getLogger(__name__)

class KeywordAnalyzer:
    """Service để phân tích từ khóa và tìm product_type_id phù hợp"""
    
    def __init__(self, llm_client: OpenAIClient, tripc_client: TripCAPIClient):
        self.llm_client = llm_client
        self.tripc_client = tripc_client
        self.product_types_cache = None
    
    async def get_all_product_types(self) -> List[Dict[str, Any]]:
        """Lấy tất cả product types từ API và cache lại"""
        if self.product_types_cache is None:
            try:
                url = f"{self.tripc_client.base_url}/api/services/product-type/all"
                response = await self.tripc_client.client.get(
                    url, 
                    headers=self.tripc_client._get_headers()
                )
                response.raise_for_status()
                data = response.json()
                self.product_types_cache = data.get("data", [])
                logger.info(f"Loaded {len(self.product_types_cache)} product types")
            except Exception as e:
                logger.error(f"Error loading product types: {e}")
                self.product_types_cache = []
        
        return self.product_types_cache
    
    def analyze_keywords(self, user_query: str) -> Dict[str, List[str]]:
        """Phân tích từ khóa từ câu hỏi người dùng sử dụng LLM"""
        
        prompt = f"""
        Phân tích câu hỏi sau và trích xuất các từ khóa quan trọng để tìm nhà hàng:

        Câu hỏi: "{user_query}"

        Hãy phân loại từ khóa theo:
        1. Danh từ riêng (Proper nouns): Tên địa điểm, tên món ăn cụ thể, tên nhà hàng
        2. Tính từ (Adjectives): Mô tả đặc điểm, phong cách, cảm giác
        3. Danh từ chung (Common nouns): Loại món ăn, loại nhà hàng, địa điểm chung

        QUY TẮC PHÂN TÍCH:
        - Nếu có "hàn quốc" → common_nouns: ["hàn quốc", "nhà hàng"]
        - Nếu có "chả cá" → common_nouns: ["chả cá", "nhà hàng"]
        - Nếu có "bbq" → common_nouns: ["bbq", "nhà hàng"]
        - Nếu có "hải sản" → common_nouns: ["hải sản", "nhà hàng"]
        - Địa điểm như "Đà Nẵng", "Hà Nội" → proper_nouns
        - Tính từ như "ngon", "đẹp", "rẻ" → adjectives

        Trả về JSON:
        {{
            "proper_nouns": ["từ1", "từ2"],
            "adjectives": ["từ1", "từ2"], 
            "common_nouns": ["từ1", "từ2"]
        }}

        Chỉ trả về JSON, không có text khác.
        """
        
        try:
            response = self.llm_client.generate_response_sync(
                prompt=prompt,
                model="gpt-4o-mini",
                max_tokens=300,
                temperature=0.3
            )
            
            if response:
                # Tìm JSON trong response
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = response[start_idx:end_idx]
                    result = json.loads(json_str)
                    logger.info(f"Analyzed keywords: {result}")
                    return result
                else:
                    logger.warning("No JSON found in LLM response")
                    return {"proper_nouns": [], "adjectives": [], "common_nouns": []}
            else:
                logger.error("LLM response is None")
                return {"proper_nouns": [], "adjectives": [], "common_nouns": []}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            return {"proper_nouns": [], "adjectives": [], "common_nouns": []}
        except Exception as e:
            logger.error(f"Error analyzing keywords: {e}")
            return {"proper_nouns": [], "adjectives": [], "common_nouns": []}
    
    def find_matching_product_types(self, keywords: Dict[str, List[str]], product_types: List[Dict[str, Any]]) -> List[int]:
        """Tìm product_type_id phù hợp dựa trên từ khóa"""
        
        if not product_types:
            return []
        
        # Tạo prompt để LLM tìm product_type_id phù hợp
        product_types_str = json.dumps(product_types, ensure_ascii=False, indent=2)
        
        prompt = f"""
        Bạn là chuyên gia phân loại nhà hàng. Dựa trên từ khóa người dùng tìm kiếm, hãy chọn product_type_id phù hợp nhất từ danh sách.

        Từ khóa người dùng tìm kiếm:
        - Danh từ riêng: {keywords.get('proper_nouns', [])}
        - Tính từ: {keywords.get('adjectives', [])}
        - Danh từ chung: {keywords.get('common_nouns', [])}

        Danh sách product types có sẵn:
        {product_types_str}

        QUY TẮC CHỌN:
        1. Chỉ chọn product_type_id có tên hoặc mô tả liên quan trực tiếp đến từ khóa
        2. Nếu tìm "hàn quốc" thì chọn product_type có tên "Hàn Quốc", "Korean", "BBQ Hàn Quốc"
        3. Nếu tìm "chả cá" thì chọn product_type có tên "Chả cá", "Cá", "Hải sản"
        4. Không chọn product_type không liên quan
        5. Ưu tiên chính xác hơn là nhiều kết quả

        Trả về JSON:
        {{
            "matching_ids": [id1, id2],
            "reasoning": "Giải thích tại sao chọn các ID này"
        }}

        Chỉ trả về JSON, không có text khác.
        """
        
        try:
            response = self.llm_client.generate_response_sync(
                prompt=prompt,
                model="gpt-4o-mini", 
                max_tokens=500,
                temperature=0.3
            )
            
            if response:
                # Tìm JSON trong response
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = response[start_idx:end_idx]
                    result = json.loads(json_str)
                    matching_ids = result.get("matching_ids", [])
                    reasoning = result.get("reasoning", "")
                    logger.info(f"Found matching product type IDs: {matching_ids}, Reasoning: {reasoning}")
                    return matching_ids
                else:
                    logger.warning("No JSON found in LLM response for product type matching")
                    return []
            else:
                logger.error("LLM response is None for product type matching")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response for product type matching: {e}")
            return []
        except Exception as e:
            logger.error(f"Error finding matching product types: {e}")
            return []
    
    async def process_user_query(self, user_query: str) -> Dict[str, Any]:
        """Xử lý câu hỏi người dùng và trả về thông tin cần thiết để tìm kiếm"""
        
        # Bước 1: Phân tích từ khóa
        keywords = self.analyze_keywords(user_query)
        
        # Bước 2: Lấy tất cả product types
        product_types = await self.get_all_product_types()
        
        # Bước 3: Tìm product_type_id phù hợp
        matching_product_type_ids = self.find_matching_product_types(keywords, product_types)
        
        # Bước 4: Trả về kết quả
        result = {
            "user_query": user_query,
            "keywords": keywords,
            "matching_product_type_ids": matching_product_type_ids,
            "province_ids": [],  # Không sử dụng province_id
            "total_product_types": len(product_types)
        }
        
        logger.info(f"Processed user query: {result}")
        return result
    
    async def search_restaurants_with_analysis(self, user_query: str, page: int = 1, page_size: int = 15) -> List[Any]:
        """Tìm kiếm nhà hàng với phân tích từ khóa và product_type_id"""
        
        # Xử lý câu hỏi người dùng
        analysis_result = await self.process_user_query(user_query)
        
        # Tìm kiếm nhà hàng chỉ với product_type_id
        restaurants = []
        
        for product_type_id in analysis_result["matching_product_type_ids"]:
            try:
                restaurant_batch = await self.tripc_client.get_restaurants(
                    page=page,
                    page_size=page_size,
                    product_type_id=product_type_id
                )
                
                # Lọc nhà hàng chỉ ở Đà Nẵng
                filtered_restaurants = []
                for restaurant in restaurant_batch:
                    # Kiểm tra xem nhà hàng có ở Đà Nẵng không
                    if restaurant.city and "đà nẵng" in restaurant.city.lower():
                        filtered_restaurants.append(restaurant)
                    elif restaurant.address and "đà nẵng" in restaurant.address.lower():
                        filtered_restaurants.append(restaurant)
                    elif restaurant.address and "danang" in restaurant.address.lower():
                        filtered_restaurants.append(restaurant)
                
                restaurants.extend(filtered_restaurants)
                
            except Exception as e:
                logger.error(f"Error searching restaurants with product_type_id={product_type_id}: {e}")
        
        # Sắp xếp theo rating và giới hạn tối đa 5 nhà hàng
        if restaurants:
            # Sắp xếp theo rating (cao nhất trước)
            restaurants.sort(key=lambda x: (x.rating is not None, x.rating or 0), reverse=True)
            # Giới hạn tối đa 5 nhà hàng
            restaurants = restaurants[:5]
        
        return {
            "restaurants": restaurants,
            "analysis": analysis_result,
            "total_found": len(restaurants)
        }
    
    async def test_province_ids(self) -> Dict[str, Any]:
        """Test các province_id để tìm province_id đúng cho Đà Nẵng"""
        
        test_province_ids = [1, 2, 3, 4, 5, 47, 48, 49, 50]
        results = {}
        
        for province_id in test_province_ids:
            try:
                # Test với product_type_id = 23 (Ẩm thực Hàn)
                restaurant_batch = await self.tripc_client.get_restaurants(
                    page=1,
                    page_size=5,
                    product_type_id=23,
                    province_id=province_id
                )
                
                # Đếm nhà hàng ở Đà Nẵng
                danang_count = 0
                for restaurant in restaurant_batch:
                    if restaurant.city and "đà nẵng" in restaurant.city.lower():
                        danang_count += 1
                    elif restaurant.address and "đà nẵng" in restaurant.address.lower():
                        danang_count += 1
                    elif restaurant.address and "danang" in restaurant.address.lower():
                        danang_count += 1
                
                results[province_id] = {
                    "total": len(restaurant_batch),
                    "danang_count": danang_count,
                    "sample_restaurants": [r.name for r in restaurant_batch[:3]]
                }
                
            except Exception as e:
                results[province_id] = {"error": str(e)}
        
        return results
    
    async def debug_matching(self, user_query: str) -> Dict[str, Any]:
        """Debug method để kiểm tra quá trình matching"""
        
        # Phân tích từ khóa
        keywords = self.analyze_keywords(user_query)
        
        # Lấy product types
        product_types = await self.get_all_product_types()
        
        # Tìm matching
        matching_ids = self.find_matching_product_types(keywords, product_types)
        
        # Tìm product types được chọn
        selected_products = []
        for pt in product_types:
            if pt.get('id') in matching_ids:
                selected_products.append({
                    'id': pt.get('id'),
                    'name': pt.get('name'),
                    'slug': pt.get('slug')
                })
        
        return {
            "user_query": user_query,
            "keywords": keywords,
            "matching_product_type_ids": matching_ids,
            "selected_products": selected_products,
            "total_product_types": len(product_types)
        }
