#!/usr/bin/env python3
"""
Test script để kiểm tra logic booking agent đã sửa
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.agents.booking_agent import BookingAgent
from app.core.conversation_memory import ConversationMemory
from app.models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType

def test_booking_extraction():
    """Test logic extract booking info"""
    print("🧪 Testing Booking Agent Extraction Logic")
    print("=" * 50)
    
    # Create booking agent
    memory = ConversationMemory()
    booking_agent = BookingAgent(memory)
    
    # Test cases
    test_cases = [
        "tuan tuan111004@gmail.com 0921214",
        "tuan",
        "Nguyễn Văn A",
        "tuan@gmail.com",
        "0921214",
        "2 người 13h",
        "Tôi muốn đặt bàn",
        "Bảo tàng Chăm ở đâu?"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: '{message}'")
        
        # Test extraction
        extracted = booking_agent._extract_booking_info(message, "vi")
        print(f"   Extracted: {extracted}")
        
        # Test if it's considered "other topic"
        is_other = booking_agent._is_asking_other_topics(message, "vi")
        print(f"   Is other topic: {is_other}")
        
        # Test combined logic
        has_extracted = any(extracted.values())
        should_continue_booking = has_extracted or not is_other
        print(f"   Should continue booking: {should_continue_booking}")

def test_booking_flow():
    """Test complete booking flow"""
    print("\n\n🎯 Testing Complete Booking Flow")
    print("=" * 50)
    
    # Create booking agent
    memory = ConversationMemory()
    booking_agent = BookingAgent(memory)
    
    # Create platform context
    platform_context = PlatformContext(
        platform=PlatformType.WEB_BROWSER,
        device=DeviceType.ANDROID,
        language=LanguageType.VIETNAMESE
    )
    
    # Simulate conversation
    conversation_id = "test_conv_123"
    
    # Step 1: User asks about booking
    print("\n1️⃣ User: 'Tôi muốn đặt bàn'")
    response1 = booking_agent.handle(conversation_id, "Tôi muốn đặt bàn", platform_context)
    print(f"   AI: {response1.answerAI[:100]}...")
    
    # Step 2: User provides name
    print("\n2️⃣ User: 'tuan'")
    response2 = booking_agent.handle(conversation_id, "tuan", platform_context)
    print(f"   AI: {response2.answerAI[:100]}...")
    
    # Step 3: User provides email and phone
    print("\n3️⃣ User: 'tuan111004@gmail.com 0921214'")
    response3 = booking_agent.handle(conversation_id, "tuan111004@gmail.com 0921214", platform_context)
    print(f"   AI: {response3.answerAI[:100]}...")
    
    # Check final state
    state = booking_agent._get_booking_state(conversation_id)
    print(f"\n📊 Final booking state: {state}")

if __name__ == "__main__":
    test_booking_extraction()
    test_booking_flow()

