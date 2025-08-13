from typing import Optional, List, Union, Dict
from pydantic import BaseModel, Field
from .platform_models import PlatformType, DeviceType, LanguageType


class ChatRequest(BaseModel):
    """Chat request schema with required platform context"""
    message: str = Field(..., description="User message content")
    platform: PlatformType = Field(..., description="Platform type (web_browser or mobile_app)")
    device: DeviceType = Field(..., description="Device type (desktop, android, ios)")
    language: LanguageType = Field(..., description="Language preference (vi or en)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Tìm nhà hàng gần đây",
                "platform": "web_browser",
                "device": "android",
                "language": "vi"
            }
        }


class Source(BaseModel):
    """Source information for responses"""
    title: str
    url: str
    imageUrl: Optional[str] = None


class Suggestion(BaseModel):
    """Suggestion for user actions"""
    label: str
    detail: Optional[str] = None
    action: str


class Service(BaseModel):
    """Service information (restaurant, tour, etc.) - App-first policy, no individual URLs"""
    id: int
    name: str
    type: str
    # Image URLs
    imageUrl: Optional[str] = None  # logo_url
    coverImageUrl: Optional[str] = None  # cover_image_url
    sealImageUrl: Optional[str] = None  # seal_image_url for culinary passport
    
    # Ratings & Reviews
    rating: Optional[float] = None
    totalReviews: Optional[int] = None
    
    # Location & Address
    address: Optional[str] = None  # full_address
    city: Optional[str] = None
    
    # Service Details
    productTypes: Optional[str] = None  # product_types
    description: Optional[str] = None
    priceRange: Optional[str] = None  # price_range
    workingHoursDisplay: Optional[str] = None  # working_hours_display
    amenities: Optional[List[str]] = None
    
    # Location coordinates (as per documentation)
    location: Optional[Dict[str, float]] = None  # {"lat": float, "lng": float}
    
    # Note: NO webURL, deeplink, lat, long, isLike fields - app-first policy
    # sealImageUrl is included for culinary passport suppliers


class QnAResponse(BaseModel):
    """QnA response with embedded sources"""
    type: str = "QnA"
    answerAI: str
    sources: List[Source]
    suggestions: List[Suggestion]
    cta: Optional[dict] = None


class ServiceResponse(BaseModel):
    """Service response with app-first policy"""
    type: str = "Service"
    answerAI: str
    services: List[Service]
    sources: List[Source]
    suggestions: List[Suggestion]
    cta: Optional[dict] = None


class ChatResponse(BaseModel):
    """Main chat response schema"""
    type: str
    answerAI: str
    services: Optional[List[Service]] = None
    sources: Optional[List[Source]] = None
    suggestions: Optional[List[Suggestion]] = None
    cta: Optional[dict] = None


class UserInfoRequest(BaseModel):
    """User info collection for booking"""
    name: str = Field(..., description="User's full name")
    email: str = Field(..., description="User's email address")
    phone: str = Field(..., description="User's phone number")
    message: Optional[str] = Field(None, description="Booking inquiry message")
    service_interest: Optional[str] = Field(None, description="Service the user is interested in")
    location: Optional[str] = Field(None, description="User's preferred location or city")
    user_id: Optional[str] = Field(None, description="User ID from session")
    platform: PlatformType = Field(PlatformType.WEB_BROWSER, description="Platform context")
    device: DeviceType = Field(DeviceType.ANDROID, description="Device context")
    language: LanguageType = Field(LanguageType.VIETNAMESE, description="Language context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Nguyễn Văn A",
                "email": "user@example.com",
                "phone": "+84901234567",
                "service_interest": "Nhà hàng hải sản",
                "message": "Muốn đặt bàn cho 4 người vào tối mai",
                "location": "Da Nang",
                "platform": "web_browser",
                "device": "android",
                "language": "vi"
            }
        }


class UserInfoResponse(BaseModel):
    """Response after collecting user info"""
    status: str
    message: str
    action: Optional[str] = None
    booking_reference: Optional[str] = None
    # Backward compatibility
    success: Optional[bool] = None