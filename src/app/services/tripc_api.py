import httpx
import requests
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
        
        # Auto-login if no token provided
        if not self.access_token:
            self.access_token = self._auto_login()
    
    def _auto_login(self) -> Optional[str]:
        """Auto-login to get TripC API token"""
        try:
            login_data = {
                "email": "haqctest123@gmail.com",
                "password": "Ha03649@"
            }
            response = requests.post(f"{self.base_url}/auth/login", json=login_data, timeout=10)
            response.raise_for_status()
            token = response.json().get("token")
            if token:
                logger.info("Auto-login successful, got TripC API token")
                return token
            else:
                logger.warning("Auto-login failed: no token in response")
                return None
        except Exception as e:
            logger.error(f"Auto-login failed: {e}")
            return None
    
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
    
    async def get_restaurants(self, page: int = 1, page_size: int = 5, 
                            city: Optional[str] = None, keyword: Optional[str] = None,
                            product_type_id: Optional[int] = None, province_id: Optional[int] = None,
                            supplier_type_slug: str = "am-thuc") -> List[Service]:
        """Get restaurant services from TripC API with advanced filtering"""
        try:
            params = {
                "page": page,
                "page_size": page_size
            }
            
            # Add optional filters
            if city and keyword:
                params["keyword"] = f"{city} {keyword}"  # Combine city and keyword
            elif city:
                params["keyword"] = city  # Use keyword for city search
            elif keyword:
                params["keyword"] = keyword  # Use keyword for general search
            if product_type_id:
                params["product_type_id"] = product_type_id
            if province_id:
                params["province_id"] = province_id
            if supplier_type_slug:
                params["supplier_type_slug"] = supplier_type_slug
            
            url = f"{self.base_url}/api/services/restaurants"
            response = await self.client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            restaurants = []
            
            # Handle case where data is None or doesn't have 'data' key
            data_items = data.get("data") if data else None
            if data_items is None:
                logger.warning(f"No data returned from restaurants API. Response: {data}")
                return []
            
            for item in data_items:
                # Extract location coordinates
                location = None
                if item.get("lat") and item.get("long"):
                    location = {
                        "lat": float(item.get("lat")),
                        "lng": float(item.get("long"))
                    }
                
                restaurant = Service(
                    id=item.get("id"),
                    name=item.get("name", ""),
                    type="restaurant",
                    # Image URLs
                    imageUrl=item.get("logo_url"),
                    coverImageUrl=item.get("cover_image_url"),
                    sealImageUrl=item.get("seal_image_url"),  # Support for culinary passport seal
                    # Ratings & Reviews
                    rating=item.get("rating"),
                    totalReviews=item.get("total_reviews"),
                    # Location & Address
                    address=item.get("full_address", item.get("address", "")),
                    city=item.get("city", ""),
                    # Service Details
                    productTypes=item.get("product_types", ""),
                    description=item.get("description", ""),
                    priceRange=item.get("price_range", ""),
                    workingHoursDisplay=item.get("working_hours_display", ""),
                    amenities=item.get("amenities", []),
                    # Location coordinates
                    location=location
                )
                restaurants.append(restaurant)
            
            return restaurants
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting restaurants: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error getting restaurants: {e}")
            return []
    
    async def get_culinary_passport_suppliers(self, page: int = 1, page_size: int = 100, 
                                            keyword: Optional[str] = None, 
                                            product_type_id: Optional[int] = None) -> List[Service]:
        """Get suppliers from Culinary Passport (Hộ chiếu ẩm thực Đà Nẵng) with keyword and product_type filtering"""
        try:
            params = {
                "page": page,
                "page_size": page_size
            }
            
            # Add keyword search if provided
            if keyword:
                params["keyword"] = keyword
            
            # Add product_type_id filter if provided
            if product_type_id:
                params["product_type_id"] = product_type_id
            
            url = f"{self.base_url}/api/culinary-passport/suppliers"
            response = await self.client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            suppliers = []
            
            for item in data.get("data", []):
                # Extract location coordinates
                location = None
                if item.get("lat") and item.get("long"):
                    location = {
                        "lat": float(item.get("lat")),
                        "lng": float(item.get("long"))
                    }
                
                supplier = Service(
                    id=item.get("id"),
                    name=item.get("name", ""),
                    type="culinary_passport",
                    # Image URLs
                    imageUrl=item.get("logo_url"),
                    coverImageUrl=item.get("cover_image_url"),
                    sealImageUrl=item.get("seal_image_url"),  # Special seal for culinary passport
                    # Ratings & Reviews
                    rating=item.get("rating"),
                    totalReviews=item.get("total_reviews"),
                    # Location & Address
                    address=item.get("full_address", item.get("address", "")),
                    city=item.get("city", ""),
                    # Service Details
                    productTypes=item.get("product_types", ""),
                    description=item.get("description", ""),
                    priceRange=item.get("price_range", ""),
                    workingHoursDisplay=item.get("working_hours_display", ""),
                    amenities=item.get("amenities", []),
                    # Location coordinates
                    location=location
                )
                suppliers.append(supplier)
            
            return suppliers
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting culinary passport suppliers: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error getting culinary passport suppliers: {e}")
            return []
    
    async def get_hotels(self, page: int = 1, page_size: int = 100, 
                        supplier_type_slug: str = "luu-tru") -> List[Service]:
        """Get hotel services from TripC API"""
        try:
            params = {
                "page": page,
                "page_size": page_size,
                "supplier_type_slug": supplier_type_slug
            }
            
            url = f"{self.base_url}/api/services/hotels"
            response = await self.client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            hotels = []
            
            for item in data.get("data", []):
                # Extract location coordinates
                location = None
                if item.get("lat") and item.get("long"):
                    try:
                        location = {
                            "lat": float(item.get("lat")),
                            "lng": float(item.get("long"))
                        }
                    except (ValueError, TypeError):
                        # Skip invalid coordinates
                        location = None
                
                hotel = Service(
                    id=item.get("id"),
                    name=item.get("name", ""),
                    type="hotel",
                    # Image URLs
                    imageUrl=item.get("logo_url"),
                    coverImageUrl=item.get("cover_image_url"),
                    sealImageUrl=item.get("seal_image_url"),
                    # Ratings & Reviews
                    rating=item.get("rating"),
                    totalReviews=item.get("total_reviews"),
                    # Location & Address
                    address=item.get("full_address", item.get("address", "")),
                    city=item.get("city", ""),
                    # Service Details
                    productTypes=item.get("product_types", ""),
                    description=item.get("description", ""),
                    priceRange=item.get("price_range", ""),
                    workingHoursDisplay=item.get("working_hours_display", ""),
                    amenities=item.get("amenities", []),
                    # Location coordinates
                    location=location
                )
                hotels.append(hotel)
            
            return hotels
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting hotels: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error getting hotels: {e}")
            return []
    
    async def get_restaurant_detail(self, restaurant_id: int) -> Optional[Service]:
        """Get detailed restaurant information"""
        try:
            url = f"{self.base_url}/api/services/restaurants/{restaurant_id}"
            response = await self.client.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            
            # Extract location coordinates
            location = None
            if data.get("lat") and data.get("long"):
                location = {
                    "lat": float(data.get("lat")),
                    "lng": float(data.get("long"))
                }
            
            restaurant = Service(
                id=data.get("id"),
                name=data.get("name", ""),
                type="restaurant",
                # Image URLs
                imageUrl=data.get("logo_url"),
                coverImageUrl=data.get("cover_image_url"),
                # Ratings & Reviews
                rating=data.get("rating"),
                totalReviews=data.get("total_reviews"),
                # Location & Address
                address=data.get("full_address", data.get("address", "")),
                city=data.get("city", ""),
                # Service Details
                productTypes=data.get("product_types", ""),
                description=data.get("description", ""),
                priceRange=data.get("price_range", ""),
                workingHoursDisplay=data.get("working_hours_display", ""),
                amenities=data.get("amenities", []),
                # Location coordinates
                location=location
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
    
    def get_service_sources(self, service_type: str = "restaurant") -> List[Source]:
        """Get metadata sources for service responses"""
        if service_type == "culinary_passport":
            return [
                Source(
                    title="Hộ chiếu ẩm thực Đà Nẵng",
                    url=f"{self.base_url}/api/culinary-passport/suppliers",
                    imageUrl="https://cdn.tripc.ai/sources/culinary-passport.jpg"
                )
            ]
        elif service_type == "hotel":
            return [
                Source(
                    title="TripC API - Khách sạn Đà Nẵng",
                    url=f"{self.base_url}/api/services/hotels?supplier_type_slug=luu-tru",
                    imageUrl="https://cdn.tripc.ai/sources/tripc-hotels.jpg"
                )
            ]
        else:  # restaurant or default
            return [
                Source(
                    title="TripC API - Nhà hàng Đà Nẵng",
                    url=f"{self.base_url}/api/services/restaurants?supplier_type_slug=am-thuc",
                    imageUrl="https://cdn.tripc.ai/sources/tripc-restaurants.jpg"
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
                    # Image URLs
                    imageUrl=item.get("logo_url"),
                    coverImageUrl=item.get("cover_image_url"),
                    sealImageUrl=item.get("seal_image_url"),
                    # Ratings & Reviews
                    rating=item.get("rating"),
                    totalReviews=item.get("total_reviews"),
                    # Location & Address
                    address=item.get("full_address", item.get("address", "")),
                    city=item.get("city", ""),
                    lat=item.get("lat"),
                    long=item.get("long"),
                    # Service Details
                    productTypes=item.get("product_types", ""),
                    description=item.get("description", ""),
                    priceRange=item.get("price_range", ""),
                    workingHoursDisplay=item.get("working_hours_display", ""),
                    amenities=item.get("amenities", []),
                    # Additional Fields
                    isLike=item.get("is_like"),
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