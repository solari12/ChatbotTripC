#!/usr/bin/env python3
"""
Test script để kiểm tra logic booking thông minh mới
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.agents.booking_agent import BookingAgent
from app.core.conversation_memory import ConversationMemory
from app.models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType

def test_smart_extraction():
    """Test smart extraction logic"""
    print("🧪 Testing Smart Booking Extraction")
    print("=" * 50)
    
    # Create booking agent
    memory = ConversationMemory()
    booking_agent = BookingAgent(memory)
    
    # Test cases
    test_cases = [
        "tôi đi với anh Quyền và Sếp Hải",
        "tuan111004@gmail.com 0921214",
        "sửa lại email",
        "chốt đơn",
        "Bảo tàng Chăm ở đâu?",
        "đi cùng vợ và 2 con",
        "tôi muốn đặt bàn lúc 7h tối"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: '{message}'")
        
        # Test LLM extraction
        state = {}
        llm_result = booking_agent._llm_extract_and_plan(state, message, "vi")
        print(f"   LLM Result: {llm_result}")
        
        # Test simple extraction
        simple_result = booking_agent._extract_booking_info(message, "vi")
        print(f"   Simple Result: {simple_result}")

async def test_booking_flow():
    """Test complete smart booking flow"""
    print("\n\n🎯 Testing Smart Booking Flow")
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
    conversation_id = "test_smart_123"
    
    # Step 1: User asks about booking
    print("\n1️⃣ User: 'Tôi muốn đặt bàn'")
    response1 = await booking_agent.handle(conversation_id, "Tôi muốn đặt bàn", platform_context)
    print(f"   AI: {response1.answerAI[:100]}...")
    
    # Step 2: User provides party info
    print("\n2️⃣ User: 'tôi đi với anh Quyền và Sếp Hải'")
    response2 = await booking_agent.handle(conversation_id, "tôi đi với anh Quyền và Sếp Hải", platform_context)
    print(f"   AI: {response2.answerAI[:100]}...")
    
    # Step 3: User provides contact info
    print("\n3️⃣ User: 'tuan111004@gmail.com 0921214'")
    response3 = await booking_agent.handle(conversation_id, "tuan111004@gmail.com 0921214", platform_context)
    print(f"   AI: {response3.answerAI[:100]}...")
    
    # Step 4: User wants to modify
    print("\n4️⃣ User: 'sửa lại email'")
    response4 = await booking_agent.handle(conversation_id, "sửa lại email", platform_context)
    print(f"   AI: {response4.answerAI[:100]}...")
    
    # Check final state
    state = booking_agent._get_booking_state(conversation_id)
    print(f"\n📊 Final booking state: {state}")

if __name__ == "__main__":
    import asyncio
    test_smart_extraction()
    asyncio.run(test_booking_flow())


