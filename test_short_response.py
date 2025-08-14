#!/usr/bin/env python3
"""
Test script để kiểm tra logic trả lời ngắn gọn
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.agents.booking_agent import BookingAgent
from app.core.conversation_memory import ConversationMemory
from app.models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType

async def test_short_response():
    """Test logic trả lời ngắn gọn"""
    print("🧠 Testing Short Response Logic")
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
    conversation_id = "short_response_123"
    
    # Test flow: User asks question during booking
    print("\n🎭 Test Flow: User hỏi câu hỏi trong lúc đặt bàn")
    print("-" * 50)
    
    print("\n👤 User: 'Tôi muốn đặt bàn'")
    response = await booking_agent.handle(conversation_id, "Tôi muốn đặt bàn", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Bảo tàng Chăm ở đâu?'")
    response = await booking_agent.handle(conversation_id, "Bảo tàng Chăm ở đâu?", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'trả lời đi'")
    response = await booking_agent.handle(conversation_id, "trả lời đi", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'tiếp tục đặt bàn'")
    response = await booking_agent.handle(conversation_id, "tiếp tục đặt bàn", platform_context)
    print(f"🤖 AI: {response.answerAI}")

def test_intent_detection():
    """Test intent detection cho short response"""
    print("\n\n🎯 Testing Intent Detection")
    print("=" * 50)
    
    memory = ConversationMemory()
    booking_agent = BookingAgent(memory)
    
    test_cases = [
        ("trả lời đi", "answer_request"),
        ("ok trả lời", "answer_request"),
        ("trả lời luôn", "answer_request"),
        ("có", "pause_booking"),
        ("được", "pause_booking"),
        ("tiếp tục", "continue_booking"),
        ("hello world", "booking_info"),  # Should not detect as special intent
    ]
    
    for message, expected_intent in test_cases:
        state = {}
        llm_result = booking_agent._llm_extract_and_plan(state, message, "vi")
        detected_intent = state.get("user_intent", "unknown")
        print(f"'{message}' -> detected: {detected_intent}, expected: {expected_intent}")

if __name__ == "__main__":
    import asyncio
    test_intent_detection()
    asyncio.run(test_short_response())

