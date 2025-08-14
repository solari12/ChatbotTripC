#!/usr/bin/env python3
"""
Test script để kiểm tra logic auto-cancel booking sau 3 câu ngoài lề
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.agents.booking_agent import BookingAgent
from app.core.conversation_memory import ConversationMemory
from app.models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType

async def test_auto_cancel_flow():
    """Test auto-cancel flow sau 3 câu ngoài lề"""
    print("🧠 Testing Auto-Cancel Flow")
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
    conversation_id = "auto_cancel_123"
    
    # Test flow: User starts booking, then asks 3 off-topic questions
    print("\n🎭 Test Flow: User đặt bàn rồi hỏi 3 câu ngoài lề")
    print("-" * 50)
    
    print("\n👤 User: 'Tôi muốn đặt bàn 4U cho 3 người'")
    response = await booking_agent.handle(conversation_id, "Tôi muốn đặt bàn 4U cho 3 người", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Bảo tàng Chăm ở đâu?'")
    response = await booking_agent.handle(conversation_id, "Bảo tàng Chăm ở đâu?", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Đà Nẵng có bãi biển nào đẹp?'")
    response = await booking_agent.handle(conversation_id, "Đà Nẵng có bãi biển nào đẹp?", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Thời tiết Đà Nẵng thế nào?'")
    response = await booking_agent.handle(conversation_id, "Thời tiết Đà Nẵng thế nào?", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    # Check state after auto-cancel
    state = booking_agent._get_booking_state(conversation_id)
    print(f"\n📊 State after auto-cancel: {state}")
    
    # Test restarting booking with saved info
    print("\n\n🎭 Test Flow: Restart booking với thông tin đã lưu")
    print("-" * 50)
    
    print("\n👤 User: 'Đặt bàn lại'")
    response = await booking_agent.handle(conversation_id, "Đặt bàn lại", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    # Check state after restart
    state = booking_agent._get_booking_state(conversation_id)
    print(f"\n📊 State after restart: {state}")

async def test_reset_counter():
    """Test reset off-topic counter khi quay lại booking"""
    print("\n\n🧪 Testing Reset Counter")
    print("=" * 50)
    
    memory = ConversationMemory()
    booking_agent = BookingAgent(memory)
    
    platform_context = PlatformContext(
        platform=PlatformType.WEB_BROWSER,
        device=DeviceType.ANDROID,
        language=LanguageType.VIETNAMESE
    )
    
    conversation_id = "reset_counter_123"
    
    print("\n👤 User: 'Tôi muốn đặt bàn'")
    response = await booking_agent.handle(conversation_id, "Tôi muốn đặt bàn", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Bảo tàng Chăm ở đâu?'")
    response = await booking_agent.handle(conversation_id, "Bảo tàng Chăm ở đâu?", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Không, tiếp tục đặt bàn'")
    response = await booking_agent.handle(conversation_id, "Không, tiếp tục đặt bàn", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    # Check if counter was reset
    state = booking_agent._get_booking_state(conversation_id)
    print(f"\n📊 State after continue: {state}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_auto_cancel_flow())
    asyncio.run(test_reset_counter())

