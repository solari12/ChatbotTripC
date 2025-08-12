from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class PlatformType(str, Enum):
    """Platform types supported by the chatbot"""
    WEB_BROWSER = "web_browser"
    MOBILE_APP = "mobile_app"


class DeviceType(str, Enum):
    """Device types supported by the chatbot"""
    DESKTOP = "desktop"
    ANDROID = "android"
    IOS = "ios"


class LanguageType(str, Enum):
    """Language types supported by the chatbot"""
    VIETNAMESE = "vi"
    ENGLISH = "en"


class PlatformContext(BaseModel):
    """Platform context for request handling"""
    platform: PlatformType
    device: DeviceType
    language: LanguageType
    
    @validator('platform', 'device')
    def validate_platform_device_compatibility(cls, v, values):
        """Validate platform and device compatibility"""
        if 'platform' in values:
            platform = values['platform']
            device = v if 'device' not in values else values['device']
            
            if platform == PlatformType.MOBILE_APP and device == DeviceType.DESKTOP:
                raise ValueError("Mobile app platform cannot be used with desktop device")
            
            if platform == PlatformType.WEB_BROWSER and device in [DeviceType.ANDROID, DeviceType.IOS]:
                # Web browser on mobile devices is valid
                pass
                
        return v


class CTAResponse(BaseModel):
    """CTA (Call-to-Action) response for platform-specific actions"""
    device: DeviceType
    label: str
    url: Optional[str] = None
    deeplink: Optional[str] = None
    
    @validator('deeplink')
    def validate_deeplink_format(cls, v):
        """Validate deeplink format for mobile app"""
        if v and not v.startswith('tripc://'):
            raise ValueError("Deeplink must start with 'tripc://'")
        return v


class AppStoreURLs:
    """App store URLs for different platforms"""
    
    @staticmethod
    def get_android_store_url() -> str:
        return "https://play.google.com/store/apps/details?id=com.tripc.ai.app"
    
    @staticmethod
    def get_ios_store_url() -> str:
        return "https://apps.apple.com/vn/app/tripc-app/id6745506417"
    
    @staticmethod
    def get_general_download_url() -> str:
        return "https://tripc.ai/mobileapp"