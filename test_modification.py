#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.agents.booking_agent import BookingAgent
from app.core.conversation_memory import ConversationMemory
from app.models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType

def test_modification_logic():
    """Test modification logic"""
    print("🧪 Testing Modification Logic")
    print("=" * 50)
    
    # Create booking agent
    memory = ConversationMemory()
    booking_agent = BookingAgent(memory)
    
    # Test modification detection
    test_cases = [
        ("ê cho sửa lại email", "email"),
        ("sửa số điện thoại", "phone"),
        ("thay đổi tên", "name"),
        ("đổi nhà hàng", "restaurant"),
        ("cập nhật thời gian", "time"),
        ("sửa số người", "party_size"),
        ("hello world", None),  # Should not detect as modification
    ]
    
    for message, expected_field in test_cases:
        is_mod = booking_agent._is_modification_request(message, "vi")
        detected_field = booking_agent._detect_field_to_modify(message, "vi")
        print(f"'{message}' -> is_mod: {is_mod}, field: {detected_field} (expected: {expected_field})")

def test_email_extraction():
    """Test email extraction"""
    print("\n\n📧 Testing Email Extraction")
    print("=" * 50)
    
    memory = ConversationMemory()
    booking_agent = BookingAgent(memory)
    
    test_emails = [
        "tuan111004@gmail.com",
        "test@example.com",
        "user.name@domain.co.uk",
        "invalid-email",
        "test@",
        "@domain.com"
    ]
    
    for email in test_emails:
        extracted = booking_agent._extract_booking_info(email, "vi")
        print(f"'{email}' -> {extracted}")

if __name__ == "__main__":
    test_modification_logic()
    test_email_extraction()

