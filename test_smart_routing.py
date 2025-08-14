#!/usr/bin/env python3
"""
Test script for smart routing logic
Tests various scenarios where user wants to continue booking vs do something else
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.agents.ai_orchestrator import AIAgentOrchestrator
from app.agents.qna_agent import QnAAgent
from app.agents.service_agent import ServiceAgent
from app.services.tripc_api import TripCAPIClient
from app.llm.rate_limited_client import RateLimitedLLMClient
from app.llm.open_client import OpenAIClient


async def test_smart_routing():
    """Test smart routing logic with various scenarios"""
    
    print("🧪 Testing Smart Routing Logic")
    print("=" * 50)
    
    # Initialize components
    llm_client = RateLimitedLLMClient(OpenAIClient())
    tripc_client = TripCAPIClient()
    
    qna_agent = QnAAgent(llm_client)
    service_agent = ServiceAgent(tripc_client, llm_client)
    
    orchestrator = AIAgentOrchestrator(qna_agent, service_agent, llm_client)
    
    # Test scenarios
    test_cases = [
        {
            "name": "Continue Booking - Provide Name",
            "message": "Tên tôi là Nguyễn Văn A",
            "original_intent": "qna",
            "expected": True,
            "description": "User providing name during booking"
        },
        {
            "name": "Continue Booking - Provide Phone",
            "message": "Số điện thoại 0901234567",
            "original_intent": "qna", 
            "expected": True,
            "description": "User providing phone during booking"
        },
        {
            "name": "Continue Booking - Confirm",
            "message": "Xác nhận đặt bàn",
            "original_intent": "qna",
            "expected": True,
            "description": "User confirming booking"
        },
        {
            "name": "Do Something Else - Service Discovery",
            "message": "Gợi ý nhà hàng khác",
            "original_intent": "service",
            "expected": False,
            "description": "User wants to discover other restaurants"
        },
        {
            "name": "Do Something Else - Information Request",
            "message": "Nhà hàng này có đẹp không?",
            "original_intent": "qna",
            "expected": False,
            "description": "User asking for information"
        },
        {
            "name": "Do Something Else - Search",
            "message": "Tìm nhà hàng hải sản",
            "original_intent": "service",
            "expected": False,
            "description": "User wants to search for restaurants"
        },
        {
            "name": "Mixed Signals - LLM Decision",
            "message": "Gợi ý nhà hàng để đặt bàn",
            "original_intent": "service",
            "expected": "llm",  # Will be decided by LLM
            "description": "Mixed signals - needs LLM decision"
        },
        {
            "name": "Already Booking Intent",
            "message": "Đặt bàn lúc 7h tối",
            "original_intent": "booking",
            "expected": True,
            "description": "Original intent is already booking"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print(f"📝 Message: '{test_case['message']}'")
        print(f"🎯 Original Intent: {test_case['original_intent']}")
        print(f"📚 Description: {test_case['description']}")
        
        try:
            # Test the routing logic
            result = orchestrator._user_wants_to_continue_booking(
                test_case["message"], 
                test_case["original_intent"]
            )
            
            print(f"🤖 Result: {result}")
            print(f"🎯 Expected: {test_case['expected']}")
            
            # Determine if test passed
            if test_case["expected"] == "llm":
                # For LLM decisions, we can't predict the exact result
                print(f"🤖 LLM Decision: {result}")
                status = "✅ LLM DECISION"
            else:
                passed = result == test_case["expected"]
                status = "✅ PASS" if passed else "❌ FAIL"
            
            print(f"{status}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("-" * 50)


async def test_conversation_flow():
    """Test complete conversation flow with smart routing"""
    
    print("\n🔄 Testing Conversation Flow with Smart Routing")
    print("=" * 50)
    
    # Initialize components
    llm_client = RateLimitedLLMClient(OpenAIClient())
    tripc_client = TripCAPIClient()
    
    qna_agent = QnAAgent(llm_client)
    service_agent = ServiceAgent(tripc_client, llm_client)
    
    orchestrator = AIAgentOrchestrator(qna_agent, service_agent, llm_client)
    
    conversation_id = "test_smart_routing"
    
    # Simulate a conversation flow
    conversation_steps = [
        {
            "message": "Tôi muốn đặt bàn",
            "expected_behavior": "Start booking flow",
            "description": "Initial booking request"
        },
        {
            "message": "Gợi ý nhà hàng",
            "expected_behavior": "Switch to service agent",
            "description": "User wants suggestions"
        },
        {
            "message": "Nhà hàng này có đẹp không?",
            "expected_behavior": "Switch to QnA agent", 
            "description": "User asking for information"
        },
        {
            "message": "Đặt bàn ở đó",
            "expected_behavior": "Switch back to booking agent",
            "description": "User wants to book"
        },
        {
            "message": "Tên tôi là Nguyễn Văn A",
            "expected_behavior": "Continue booking",
            "description": "User providing name"
        }
    ]
    
    for i, step in enumerate(conversation_steps, 1):
        print(f"\n🔄 Step {i}: {step['description']}")
        print(f"📝 Message: '{step['message']}'")
        print(f"🎯 Expected: {step['expected_behavior']}")
        
        try:
            # Create state
            state = {
                "message": step["message"],
                "platform": "web_browser",
                "device": "desktop",
                "language": "vi", 
                "conversationId": conversation_id
            }
            
            # Run intent classification
            result_state = await orchestrator._classify_intent(state)
            
            intent = result_state.get("intent")
            needs_clarification = result_state.get("needs_clarification", False)
            
            print(f"🤖 Intent: {intent}")
            print(f"❓ Needs Clarification: {needs_clarification}")
            
            # Add to conversation history for next step
            orchestrator.memory.add_turn(
                conversation_id=conversation_id,
                role="user",
                content=step["message"]
            )
            
            # Simulate assistant response
            orchestrator.memory.add_turn(
                conversation_id=conversation_id,
                role="assistant",
                content=f"Response for {intent} intent"
            )
            
            # Update entities based on intent
            if intent == "booking":
                orchestrator.memory.update_entities_safe(conversation_id, {
                    "booking": {"status": "collecting"}
                }, "test")
            elif intent == "service":
                orchestrator.memory.update_entities_safe(conversation_id, {
                    "current_place": "Test Restaurant"
                }, "test")
            
            print(f"✅ Step completed")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("-" * 30)


if __name__ == "__main__":
    print("🚀 Starting Smart Routing Tests")
    
    # Run tests
    asyncio.run(test_smart_routing())
    asyncio.run(test_conversation_flow())
    
    print("\n✨ Testing completed!")

