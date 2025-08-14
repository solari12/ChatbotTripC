#!/usr/bin/env python3
"""
Test script để kiểm tra logic pause/continue booking
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.agents.booking_agent import BookingAgent
from app.core.conversation_memory import ConversationMemory
from app.models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType

async def test_pause_continue_flow():
    """Test pause/continue booking flow"""
    print("🧪 Testing Pause/Continue Booking Flow")
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
    conversation_id = "test_pause_123"
    
    # Step 1: Start booking
    print("\n1️⃣ User: 'Tôi muốn đặt bàn'")
    response1 = await booking_agent.handle(conversation_id, "Tôi muốn đặt bàn", platform_context)
    print(f"   AI: {response1.answerAI[:100]}...")
    
    # Step 2: User asks other question
    print("\n2️⃣ User: 'Bảo tàng Chăm ở đâu?'")
    response2 = await booking_agent.handle(conversation_id, "Bảo tàng Chăm ở đâu?", platform_context)
    print(f"   AI: {response2.answerAI[:100]}...")
    
    # Step 3: User wants to pause booking to get answer
    print("\n3️⃣ User: 'có'")
    response3 = await booking_agent.handle(conversation_id, "có", platform_context)
    print(f"   AI: {response3.answerAI[:100]}...")
    
    # Step 4: User wants to continue booking
    print("\n4️⃣ User: 'tiếp tục đặt bàn'")
    response4 = await booking_agent.handle(conversation_id, "tiếp tục đặt bàn", platform_context)
    print(f"   AI: {response4.answerAI[:100]}...")
    
    # Check final state
    state = booking_agent._get_booking_state(conversation_id)
    print(f"\n📊 Final booking state: {state}")

def test_intent_detection():
    """Test intent detection for pause/continue"""
    print("\n\n🎯 Testing Intent Detection")
    print("=" * 50)
    
    memory = ConversationMemory()
    booking_agent = BookingAgent(memory)
    
    test_cases = [
        ("có", "pause_booking"),
        ("được", "pause_booking"),
        ("ok", "pause_booking"),
        ("tiếp tục", "continue_booking"),
        ("tiếp tục đặt bàn", "continue_booking"),
        ("quay lại đặt bàn", "continue_booking"),
        ("hello world", "booking_info"),  # Should not detect as pause/continue
    ]
    
    for message, expected_intent in test_cases:
        state = {}
        llm_result = booking_agent._llm_extract_and_plan(state, message, "vi")
        detected_intent = state.get("user_intent", "unknown")
        print(f"'{message}' -> detected: {detected_intent}, expected: {expected_intent}")

if __name__ == "__main__":
    import asyncio
    test_intent_detection()
    asyncio.run(test_pause_continue_flow())

