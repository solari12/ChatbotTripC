#!/usr/bin/env python3
"""
Test script để debug logic confirmation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.agents.booking_agent import BookingAgent
from app.core.conversation_memory import ConversationMemory
from app.models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType

async def test_debug_confirmation():
    """Debug confirmation logic"""
    print("🧠 Debug Confirmation Logic")
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
    conversation_id = "debug_confirmation_123"
    
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
    
    # Test "được" specifically
    message = "được"
    print(f"\n👤 User: '{message}'")
    
    # Call LLM first to see what intent it returns
    llm_result = booking_agent._llm_extract_and_plan(state, message, "vi")
    print(f"🤖 LLM Intent: {state.get('user_intent', 'unknown')}")
    print(f"🤖 LLM Action: {state.get('next_action', 'unknown')}")
    
    # Now call handle to see if heuristic kicks in
    response = await booking_agent.handle(conversation_id, message, platform_context)
    print(f"🤖 Final Response: {response.answerAI[:100]}...")
    
    # Check final state
    final_state = booking_agent._get_booking_state(conversation_id)
    print(f"🤖 Final Intent: {final_state.get('user_intent', 'unknown')}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_debug_confirmation())

