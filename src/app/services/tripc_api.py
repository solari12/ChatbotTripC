import httpx
from typing import List, Optional, Dict, Any
from ..models.schemas import Service, Source
import logging

logger = logging.getLogger(__name__)


class TripCAPIClient:
    """Client for integrating with TripC API ecosystem"""
    
    def __init__(self, base_url: str = "https://api.tripc.ai", access_token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    async def get_restaurants(self, page: int = 1, page_size: int = 10, 
                            city: Optional[str] = None) -> List[Service]:
        """Get restaurant services from TripC API"""
        try:
            params = {
                "page": page,
                "page_size": page_size
            }
            if city:
                params["city"] = city
            
            url = f"{self.base_url}/api/services/restaurants"
            response = await self.client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            restaurants = []
            
            for item in data.get("data", []):
                restaurant = Service(
                    id=item.get("id"),
                    name=item.get("name", ""),
                    type="restaurant",
                    imageUrl=item.get("logo_url") or item.get("cover_image_url"),
                    coverImageUrl=item.get("cover_image_url"),
                    rating=item.get("rating"),
                    totalReviews=item.get("total_reviews"),
                    address=item.get("address", ""),
                    city=item.get("city", ""),
                    productTypes=item.get("product_types", ""),
                    description=item.get("description", ""),
                    priceRange=item.get("price_range", ""),
                    workingHoursDisplay=item.get("working_hours_display", ""),
                    amenities=item.get("amenities", []),
                    location=item.get("location")
                )
                restaurants.append(restaurant)
            
            return restaurants
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting restaurants: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error getting restaurants: {e}")
            return []
    
    async def get_restaurant_detail(self, restaurant_id: int) -> Optional[Service]:
        """Get detailed restaurant information"""
        try:
            url = f"{self.base_url}/api/services/restaurants/{restaurant_id}"
            response = await self.client.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            restaurant = Service(
                id=data.get("id"),
                name=data.get("name", ""),
                type="restaurant",
                imageUrl=data.get("logo_url") or data.get("cover_image_url"),
                coverImageUrl=data.get("cover_image_url"),
                rating=data.get("rating"),
                totalReviews=data.get("total_reviews"),
                address=data.get("address", ""),
                city=data.get("city", ""),
                productTypes=data.get("product_types", ""),
                description=data.get("description", ""),
                priceRange=data.get("price_range", ""),
                workingHoursDisplay=data.get("working_hours_display", ""),
                amenities=data.get("amenities", []),
                location=data.get("location")
            )
            
            return restaurant
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting restaurant {restaurant_id}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting restaurant {restaurant_id}: {e}")
            return None
    
    async def get_seating_info(self, restaurant_id: int) -> Optional[Dict[str, Any]]:
        """Get restaurant seating information"""
        try:
            url = f"{self.base_url}/api/services/seating/{restaurant_id}"
            response = await self.client.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting seating info for {restaurant_id}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting seating info for {restaurant_id}: {e}")
            return None
    
    def get_service_sources(self) -> List[Source]:
        """Get metadata sources for service responses"""
        return [
            Source(
                title="TripC API - Nhà hàng Đà Nẵng",
                url=f"{self.base_url}/api/services/restaurants",
                imageUrl="https://cdn.tripc.ai/sources/tripc-api.jpg"
            )
        ]
    
    async def search_services(self, query: str, service_type: str = "restaurant", 
                            page: int = 1, page_size: int = 10) -> List[Service]:
        """Search for services by query"""
        try:
            params = {
                "q": query,
                "type": service_type,
                "page": page,
                "page_size": page_size
            }
            
            url = f"{self.base_url}/api/services/search"
            response = await self.client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            services = []
            
            for item in data.get("data", []):
                service = Service(
                    id=item.get("id"),
                    name=item.get("name", ""),
                    type=item.get("type", service_type),
                    imageUrl=item.get("logo_url") or item.get("cover_image_url"),
                    coverImageUrl=item.get("cover_image_url"),
                    rating=item.get("rating"),
                    totalReviews=item.get("total_reviews"),
                    address=item.get("address", ""),
                    city=item.get("city", ""),
                    productTypes=item.get("product_types", ""),
                    description=item.get("description", ""),
                    priceRange=item.get("price_range", ""),
                    workingHoursDisplay=item.get("working_hours_display", ""),
                    amenities=item.get("amenities", []),
                    location=item.get("location")
                )
                services.append(service)
            
            return services
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error searching services: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error searching services: {e}")
            return []
    
    def set_access_token(self, token: str):
        """Set or update access token"""
        self.access_token = token