from typing import Optional
from ..models.platform_models import (
    CTAResponse, DeviceType, PlatformType, AppStoreURLs
)
from ..models.schemas import Service


class CTAEngine:
    """Engine for generating platform-specific Call-to-Actions"""
    
    def __init__(self):
        self.app_store_urls = AppStoreURLs()
    
    def generate_web_cta(self, device: DeviceType, service_id: Optional[int] = None) -> CTAResponse:
        """Generate CTA for web browser users (app download)"""
        if device == DeviceType.ANDROID:
            return CTAResponse(
                device=device,
                label="Tải app TripC cho Android",
                url=self.app_store_urls.get_android_store_url()
            )
        elif device == DeviceType.IOS:
            return CTAResponse(
                device=device,
                label="Tải app TripC cho iOS",
                url=self.app_store_urls.get_ios_store_url()
            )
        else:  # desktop
            return CTAResponse(
                device=device,
                label="Tải app TripC để trải nghiệm tốt hơn",
                url=self.app_store_urls.get_general_download_url()
            )
    
    def generate_app_cta(self, device: DeviceType, service_id: int, service_type: str = "restaurant") -> CTAResponse:
        """Generate CTA for mobile app users (deeplinks)"""
        deeplink = f"tripc://{service_type}/{service_id}"
        
        return CTAResponse(
            device=device,
            label=f"Xem chi tiết {service_type}",
            deeplink=deeplink
        )
    
    def generate_platform_cta(self, platform: PlatformType, device: DeviceType, 
                            service_id: Optional[int] = None, service_type: str = "restaurant") -> CTAResponse:
        """Generate platform-appropriate CTA"""
        if platform == PlatformType.WEB_BROWSER:
            return self.generate_web_cta(device, service_id)
        elif platform == PlatformType.MOBILE_APP:
            if service_id is None:
                # Fallback for general app CTA
                return self.generate_web_cta(device)
            return self.generate_app_cta(device, service_id, service_type)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    def generate_service_cta(self, platform: PlatformType, device: DeviceType, 
                           services: list) -> Optional[CTAResponse]:
        """Generate CTA for service responses"""
        if not services:
            return None
        
        # Use first service for CTA generation
        first_service = services[0]
        service_id = first_service.id if hasattr(first_service, 'id') else None
        service_type = first_service.type if hasattr(first_service, 'type') else "restaurant"
        
        return self.generate_platform_cta(platform, device, service_id, service_type)
    
    def get_cta_for_language(self, cta: CTAResponse, language: str) -> CTAResponse:
        """Localize CTA labels based on language"""
        if language == "vi":
            # Vietnamese labels (default)
            return cta
        elif language == "en":
            # English labels
            if "Tải app" in cta.label:
                cta.label = cta.label.replace("Tải app", "Download app")
            if "cho Android" in cta.label:
                cta.label = cta.label.replace("cho Android", "for Android")
            if "cho iOS" in cta.label:
                cta.label = cta.label.replace("cho iOS", "for iOS")
            if "để trải nghiệm tốt hơn" in cta.label:
                cta.label = cta.label.replace("để trải nghiệm tốt hơn", "for better experience")
            if "Xem chi tiết" in cta.label:
                cta.label = cta.label.replace("Xem chi tiết", "View details")
        
        return cta