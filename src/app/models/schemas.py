from typing import Optional, List, Union
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
    """Service information (restaurant, tour, etc.)"""
    id: int
    name: str
    type: str
    imageUrl: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    priceRange: Optional[str] = None
    # Note: NO webURL or deeplink fields - app-first policy


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
    message: str = Field(..., description="Booking inquiry message")
    platform: PlatformType = Field(..., description="Platform context")
    device: DeviceType = Field(..., description="Device context")
    language: LanguageType = Field(..., description="Language context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Nguyễn Văn A",
                "email": "user@example.com",
                "phone": "+84901234567",
                "message": "Tôi muốn đặt bàn tại nhà hàng Bông",
                "platform": "web_browser",
                "device": "android",
                "language": "vi"
            }
        }


class UserInfoResponse(BaseModel):
    """Response after collecting user info"""
    success: bool
    message: str
    booking_reference: Optional[str] = None