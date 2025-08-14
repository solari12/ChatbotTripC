#!/usr/bin/env python3
"""
Test script for enhanced intent reasoning capabilities
Tests various complex scenarios with context and conversation history
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
from app.models.platform_models import PlatformContext, PlatformType, DeviceType, LanguageType


async def test_intent_reasoning_with_context():
    """Test enhanced intent reasoning with real conversation context"""
    
    print("🧪 Testing Enhanced Intent Reasoning with Context")
    print("=" * 60)
    
    # Initialize components
    llm_client = RateLimitedLLMClient(OpenAIClient())
    tripc_client = TripCAPIClient()
    
    qna_agent = QnAAgent(llm_client)
    service_agent = ServiceAgent(tripc_client, llm_client)
    
    orchestrator = AIAgentOrchestrator(qna_agent, service_agent, llm_client)
    
    # Test scenarios with real context
    test_cases = [
        {
            "name": "Ambiguous Intent with Context - Should Clarify",
            "message": "Đó có đẹp không?",
            "expected": "clarification",
            "context": {
                "recent_conversation": [
                    {"role": "user", "content": "Tôi muốn tìm nhà hàng hải sản"},
                    {"role": "assistant", "content": "Tôi tìm thấy nhà hàng Hải Sản Biển Đông và nhà hàng Cá Voi"},
                    {"role": "user", "content": "Nhà hàng nào ngon hơn?"},
                    {"role": "assistant", "content": "Cả hai đều ngon, nhưng Hải Sản Biển Đông có view đẹp hơn"}
                ],
                "entities": {
                    "current_place": "Hải Sản Biển Đông",
                    "last_mentioned_place": "Cá Voi",
                    "current_topic": "nhà hàng hải sản"
                }
            }
        },
        {
            "name": "Booking Flow Continuation with Context",
            "message": "Tên tôi là Nguyễn Văn A",
            "expected": "booking",
            "context": {
                "recent_conversation": [
                    {"role": "user", "content": "Tôi muốn đặt bàn"},
                    {"role": "assistant", "content": "Bạn muốn đặt bàn ở đâu?"},
                    {"role": "user", "content": "Ở nhà hàng Hải Sản Biển Đông"},
                    {"role": "assistant", "content": "Bạn muốn đặt bàn cho mấy người?"},
                    {"role": "user", "content": "4 người"},
                    {"role": "assistant", "content": "Bạn muốn đặt vào lúc nào?"},
                    {"role": "user", "content": "7h tối nay"}
                ],
                "entities": {
                    "booking": {
                        "status": "collecting",
                        "restaurant": "Hải Sản Biển Đông",
                        "party_size": "4",
                        "time": "7h tối nay"
                    }
                }
            }
        },
        {
            "name": "Pronoun Resolution with Context",
            "message": "Ở đó có đẹp không?",
            "expected": "qna",
            "context": {
                "recent_conversation": [
                    {"role": "user", "content": "Tôi muốn tìm nhà hàng hải sản"},
                    {"role": "assistant", "content": "Tôi gợi ý nhà hàng Hải Sản Biển Đông"},
                    {"role": "user", "content": "Nhà hàng đó ở đâu?"},
                    {"role": "assistant", "content": "Nhà hàng Hải Sản Biển Đông ở đường Bạch Đằng, quận Hải Châu"}
                ],
                "entities": {
                    "current_place": "Hải Sản Biển Đông",
                    "last_mentioned_place": "Hải Sản Biển Đông",
                    "current_topic": "nhà hàng hải sản"
                }
            }
        },
        {
            "name": "Service Intent with Context",
            "message": "Tìm thêm nhà hàng khác",
            "expected": "service",
            "context": {
                "recent_conversation": [
                    {"role": "user", "content": "Tôi muốn tìm nhà hàng hải sản"},
                    {"role": "assistant", "content": "Tôi gợi ý nhà hàng Hải Sản Biển Đông"},
                    {"role": "user", "content": "Nhà hàng đó có đẹp không?"},
                    {"role": "assistant", "content": "Có, nhà hàng này có view biển rất đẹp"}
                ],
                "entities": {
                    "current_place": "Hải Sản Biển Đông",
                    "last_mentioned_place": "Hải Sản Biển Đông"
                }
            }
        },
        {
            "name": "QnA Intent with Context",
            "message": "Nhà hàng này có giá cả như thế nào?",
            "expected": "qna",
            "context": {
                "recent_conversation": [
                    {"role": "user", "content": "Tôi muốn tìm nhà hàng hải sản"},
                    {"role": "assistant", "content": "Tôi gợi ý nhà hàng Hải Sản Biển Đông"},
                    {"role": "user", "content": "Nhà hàng đó có đẹp không?"},
                    {"role": "assistant", "content": "Có, nhà hàng này có view biển rất đẹp"}
                ],
                "entities": {
                    "current_place": "Hải Sản Biển Đông",
                    "last_mentioned_place": "Hải Sản Biển Đông"
                }
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print(f"📝 Message: '{test_case['message']}'")
        print(f"🎯 Expected: {test_case['expected']}")
        
        try:
            # Create conversation context
            conversation_id = f"test_context_{i}"
            
            # Set up conversation history
            context = test_case["context"]
            for turn in context.get("recent_conversation", []):
                orchestrator.memory.add_turn(
                    conversation_id=conversation_id,
                    role=turn["role"],
                    content=turn["content"]
                )
            
            # Set up entities
            if context.get("entities"):
                orchestrator.memory.set_entities(conversation_id, context["entities"])
            
            # Create state
            state = {
                "message": test_case["message"],
                "platform": "web_browser",
                "device": "desktop", 
                "language": "vi",
                "conversationId": conversation_id
            }
            
            # Run intent classification
            result_state = await orchestrator._classify_intent(state)
            
            intent = result_state.get("intent")
            needs_clarification = result_state.get("needs_clarification", False)
            clarify_question = result_state.get("clarify_question", "")
            
            print(f"🤖 Actual Intent: {intent}")
            print(f"❓ Needs Clarification: {needs_clarification}")
            if clarify_question:
                print(f"💭 Clarification Question: '{clarify_question}'")
            
            # Determine if test passed
            if test_case["expected"] == "clarification":
                passed = needs_clarification
            else:
                passed = intent == test_case["expected"]
            
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("-" * 60)


async def test_real_conversation_flow():
    """Test a complete conversation flow with context building"""
    
    print("\n🔄 Testing Real Conversation Flow")
    print("=" * 60)
    
    # Initialize components
    llm_client = RateLimitedLLMClient(OpenAIClient())
    tripc_client = TripCAPIClient()
    
    qna_agent = QnAAgent(llm_client)
    service_agent = ServiceAgent(tripc_client, llm_client)
    
    orchestrator = AIAgentOrchestrator(qna_agent, service_agent, llm_client)
    
    conversation_id = "test_real_conversation"
    
    # Simulate a real conversation flow
    conversation_steps = [
        {
            "message": "Tôi muốn tìm nhà hàng hải sản",
            "expected_intent": "service",
            "description": "Initial service request"
        },
        {
            "message": "Nhà hàng này có đẹp không?",
            "expected_intent": "qna", 
            "description": "Follow-up question about the restaurant"
        },
        {
            "message": "Đặt bàn ở đó lúc 7h tối",
            "expected_intent": "booking",
            "description": "Booking request with pronoun"
        },
        {
            "message": "Tên tôi là Nguyễn Văn A",
            "expected_intent": "booking",
            "description": "Providing name during booking"
        },
        {
            "message": "Số điện thoại 0901234567",
            "expected_intent": "booking",
            "description": "Providing phone during booking"
        }
    ]
    
    for i, step in enumerate(conversation_steps, 1):
        print(f"\n🔄 Step {i}: {step['description']}")
        print(f"📝 Message: '{step['message']}'")
        print(f"🎯 Expected Intent: {step['expected_intent']}")
        
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
            
            print(f"🤖 Actual Intent: {intent}")
            print(f"❓ Needs Clarification: {needs_clarification}")
            
            # Check if passed
            passed = intent == step["expected_intent"] and not needs_clarification
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}")
            
            # Add this turn to conversation history for next step
            orchestrator.memory.add_turn(
                conversation_id=conversation_id,
                role="user",
                content=step["message"]
            )
            
            # Simulate assistant response for context building
            if intent == "service":
                orchestrator.memory.add_turn(
                    conversation_id=conversation_id,
                    role="assistant", 
                    content="Tôi tìm thấy nhà hàng Hải Sản Biển Đông"
                )
                orchestrator.memory.update_entities_safe(conversation_id, {
                    "current_place": "Hải Sản Biển Đông",
                    "last_mentioned_place": "Hải Sản Biển Đông"
                }, "test")
            elif intent == "qna":
                orchestrator.memory.add_turn(
                    conversation_id=conversation_id,
                    role="assistant",
                    content="Nhà hàng này có view biển rất đẹp"
                )
            elif intent == "booking":
                orchestrator.memory.add_turn(
                    conversation_id=conversation_id,
                    role="assistant", 
                    content="Tôi sẽ giúp bạn đặt bàn"
                )
                # Update booking state
                current_entities = orchestrator.memory.get_entities(conversation_id)
                booking_state = current_entities.get("booking", {})
                if "tên" in step["message"].lower() or "name" in step["message"].lower():
                    booking_state["name"] = "Nguyễn Văn A"
                elif "điện thoại" in step["message"].lower() or "phone" in step["message"].lower():
                    booking_state["phone"] = "0901234567"
                booking_state["status"] = "collecting"
                orchestrator.memory.update_entities_safe(conversation_id, {
                    "booking": booking_state
                }, "test")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("-" * 40)


if __name__ == "__main__":
    print("🚀 Starting Enhanced Intent Reasoning Tests with Context")
    
    # Run tests
    asyncio.run(test_intent_reasoning_with_context())
    asyncio.run(test_real_conversation_flow())
    
    print("\n✨ Testing completed!")
