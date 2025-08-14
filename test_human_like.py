#!/usr/bin/env python3
"""
Test script thông minh hơn - giống như con người thật sự tương tác
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.agents.booking_agent import BookingAgent
from app.core.conversation_memory import ConversationMemory
from app.models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType

async def test_human_like_conversation():
    """Test conversation giống như con người thật sự"""
    print("🧠 Testing Human-Like Conversation")
    print("=" * 60)
    
    # Create booking agent
    memory = ConversationMemory()
    booking_agent = BookingAgent(memory)
    
    # Create platform context
    platform_context = PlatformContext(
        platform=PlatformType.WEB_BROWSER,
        device=DeviceType.ANDROID,
        language=LanguageType.VIETNAMESE
    )
    
    # Simulate real human conversation
    conversation_id = "human_like_123"
    
    # Scenario 1: User starts booking but gets distracted
    print("\n🎭 SCENARIO 1: User bắt đầu đặt bàn nhưng bị phân tâm")
    print("-" * 50)
    
    print("\n👤 User: 'Ê, tôi muốn đặt bàn ở 4U'")
    response = await booking_agent.handle(conversation_id, "Ê, tôi muốn đặt bàn ở 4U", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'À mà khoan, 4U có mở cửa đến mấy giờ vậy?'")
    response = await booking_agent.handle(conversation_id, "À mà khoan, 4U có mở cửa đến mấy giờ vậy?", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Ok, vậy tôi đi với vợ và 2 con'")
    response = await booking_agent.handle(conversation_id, "Ok, vậy tôi đi với vợ và 2 con", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    # Scenario 2: User provides info in natural way
    print("\n\n🎭 SCENARIO 2: User cung cấp thông tin một cách tự nhiên")
    print("-" * 50)
    
    print("\n👤 User: 'Tên tôi là Nguyễn Văn Tuấn, email tuan@gmail.com, số điện thoại 0901234567'")
    response = await booking_agent.handle(conversation_id, "Tên tôi là Nguyễn Văn Tuấn, email tuan@gmail.com, số điện thoại 0901234567", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    # Scenario 3: User changes mind and modifies info
    print("\n\n🎭 SCENARIO 3: User thay đổi ý định và sửa thông tin")
    print("-" * 50)
    
    print("\n👤 User: 'À mà thôi, sửa lại email thành tuan.nguyen@gmail.com'")
    response = await booking_agent.handle(conversation_id, "À mà thôi, sửa lại email thành tuan.nguyen@gmail.com", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Và thêm 1 người nữa, tôi đi với vợ, 2 con và mẹ tôi'")
    response = await booking_agent.handle(conversation_id, "Và thêm 1 người nữa, tôi đi với vợ, 2 con và mẹ tôi", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    # Scenario 4: User asks random questions during booking
    print("\n\n🎭 SCENARIO 4: User hỏi câu hỏi ngẫu nhiên trong lúc đặt bàn")
    print("-" * 50)
    
    print("\n👤 User: 'À mà này, Đà Nẵng có bãi biển nào đẹp nhất?'")
    response = await booking_agent.handle(conversation_id, "À mà này, Đà Nẵng có bãi biển nào đẹp nhất?", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Có'")
    response = await booking_agent.handle(conversation_id, "Có", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Ok, giờ quay lại đặt bàn'")
    response = await booking_agent.handle(conversation_id, "Ok, giờ quay lại đặt bàn", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    # Scenario 5: User confirms booking
    print("\n\n🎭 SCENARIO 5: User xác nhận đặt bàn")
    print("-" * 50)
    
    print("\n👤 User: 'Chốt luôn'")
    response = await booking_agent.handle(conversation_id, "Chốt luôn", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    # Check final state
    state = booking_agent._get_booking_state(conversation_id)
    print(f"\n📊 Final booking state: {state}")

async def test_edge_cases():
    """Test các trường hợp edge cases thông minh"""
    print("\n\n🧪 Testing Edge Cases")
    print("=" * 60)
    
    memory = ConversationMemory()
    booking_agent = BookingAgent(memory)
    
    platform_context = PlatformContext(
        platform=PlatformType.WEB_BROWSER,
        device=DeviceType.ANDROID,
        language=LanguageType.VIETNAMESE
    )
    
    conversation_id = "edge_cases_123"
    
    # Edge case 1: User provides incomplete info
    print("\n🎯 Edge Case 1: User cung cấp thông tin không đầy đủ")
    print("-" * 50)
    
    print("\n👤 User: 'Tôi muốn đặt bàn'")
    response = await booking_agent.handle(conversation_id, "Tôi muốn đặt bàn", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Tôi đi với bạn'")
    response = await booking_agent.handle(conversation_id, "Tôi đi với bạn", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    # Edge case 2: User changes topic multiple times
    print("\n\n🎯 Edge Case 2: User thay đổi chủ đề nhiều lần")
    print("-" * 50)
    
    print("\n👤 User: 'Bảo tàng Chăm có đẹp không?'")
    response = await booking_agent.handle(conversation_id, "Bảo tàng Chăm có đẹp không?", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Không, tiếp tục đặt bàn'")
    response = await booking_agent.handle(conversation_id, "Không, tiếp tục đặt bàn", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'À mà này, thời tiết Đà Nẵng thế nào?'")
    response = await booking_agent.handle(conversation_id, "À mà này, thời tiết Đà Nẵng thế nào?", platform_context)
    print(f"🤖 AI: {response.answerAI}")
    
    print("\n👤 User: 'Có'")
    response = await booking_agent.handle(conversation_id, "Có", platform_context)
    print(f"🤖 AI: {response.answerAI}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_human_like_conversation())
    asyncio.run(test_edge_cases())

