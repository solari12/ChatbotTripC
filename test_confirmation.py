#!/usr/bin/env python3
"""
Test script để kiểm tra logic confirmation booking
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.agents.booking_agent import BookingAgent
from app.core.conversation_memory import ConversationMemory
from app.models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType

async def test_confirmation_flow():
    """Test confirmation flow"""
    print("🧠 Testing Confirmation Flow")
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
    conversation_id = "confirmation_123"
    
    # Test flow: Complete booking then confirm
    print("\n🎭 Test Flow: Hoàn thành booking rồi xác nhận")
    print("-" * 50)
    
    print("\n👤 User: 'Tôi muốn đặt bàn 4U cho 3 người'")
    response = await booking_agent.handle(conversation_id, "Tôi muốn đặt bàn 4U cho 3 người", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: '3h40'")
    response = await booking_agent.handle(conversation_id, "3h40", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'tuan tuan111004@gmail.com 0921214'")
    response = await booking_agent.handle(conversation_id, "tuan tuan111004@gmail.com 0921214", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'chốt thôi'")
    response = await booking_agent.handle(conversation_id, "chốt thôi", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    # Check state after confirmation
    state = booking_agent._get_booking_state(conversation_id)
    print(f"\n📊 State after confirmation: {state}")

async def test_confirmation_keywords():
    """Test các từ khóa confirmation khác nhau"""
    print("\n\n🧪 Testing Confirmation Keywords")
    print("=" * 50)
    
    memory = ConversationMemory()
    booking_agent = BookingAgent(memory)
    
    platform_context = PlatformContext(
        platform=PlatformType.WEB_BROWSER,
        device=DeviceType.ANDROID,
        language=LanguageType.VIETNAMESE
    )
    
    conversation_id = "confirmation_keywords_123"
    
    # Setup booking state
    state = {
        "status": "collecting",
        "name": "Tuấn",
        "email": "tuan111004@gmail.com",
        "phone": "0921214",
        "restaurant": "4U",
        "party_size": "3",
        "time": "3h40",
        "special_request": None,
        "confirmed": False,
        "off_topic_count": 0,
        "last_booking_activity": "updated_time",
    }
    booking_agent._set_booking_state(conversation_id, state)
    
    test_keywords = [
        "chốt thôi",
        "xác nhận",
        "ok",
        "được",
        "chốt",
        "confirm",
    ]
    
    for keyword in test_keywords:
        print(f"\n👤 User: '{keyword}'")
        response = await booking_agent.handle(conversation_id, keyword, platform_context)
        print(f"🤖 AI: {response.answerAI[:100]}...")
        
        # Reset state for next test
        state["confirmed"] = False
        state["status"] = "collecting"
        booking_agent._set_booking_state(conversation_id, state)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_confirmation_flow())
    asyncio.run(test_confirmation_keywords())

