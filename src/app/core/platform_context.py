from typing import Optional
from ..models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType
from ..models.schemas import ChatRequest


class PlatformContextHandler:
    """Handles platform context detection and validation"""
    
    def __init__(self):
        self.supported_platforms = {
            PlatformType.WEB_BROWSER: [DeviceType.DESKTOP, DeviceType.ANDROID, DeviceType.IOS],
            PlatformType.MOBILE_APP: [DeviceType.ANDROID, DeviceType.IOS]
        }
    
    def validate_platform_compatibility(self, platform: PlatformType, device: DeviceType) -> bool:
        """Validate platform and device compatibility"""
        if platform not in self.supported_platforms:
            return False
        
        return device in self.supported_platforms[platform]
    
    def create_context(self, request: ChatRequest) -> PlatformContext:
        """Create platform context from request"""
        # Validate platform-device compatibility
        if not self.validate_platform_compatibility(request.platform, request.device):
            raise ValueError(
                f"Invalid platform-device combination: {request.platform} with {request.device}"
            )
        
        return PlatformContext(
            platform=request.platform,
            device=request.device,
            language=request.language
        )
    
    def get_platform_info(self, context: PlatformContext) -> dict:
        """Get platform information for logging/debugging"""
        return {
            "platform": context.platform.value,
            "device": context.device.value,
            "language": context.language.value,
            "is_mobile": context.device in [DeviceType.ANDROID, DeviceType.IOS],
            "is_web": context.platform == PlatformType.WEB_BROWSER,
            "is_app": context.platform == PlatformType.MOBILE_APP
        }
    
    def should_show_app_download_cta(self, context: PlatformContext) -> bool:
        """Determine if app download CTA should be shown"""
        return context.platform == PlatformType.WEB_BROWSER
    
    def should_show_deeplink_cta(self, context: PlatformContext) -> bool:
        """Determine if deeplink CTA should be shown"""
        return context.platform == PlatformType.MOBILE_APP