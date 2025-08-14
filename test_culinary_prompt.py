import asyncio
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from app.agents.service_agent import ServiceAgent
    from app.services.tripc_api import TripCAPIClient
    from app.models.platform_models import PlatformContext, LanguageType, PlatformType, DeviceType
    from app.llm.open_client import OpenAIClient
    from app.llm.rate_limited_client import RateLimitedLLMClient
    print("✅ Imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

async def test_culinary_passport_prompt():
    """Test culinary passport mention in AI responses"""
    
    print("🎯 TESTING CULINARY PASSPORT PROMPT")
    print("=" * 60)
    
    # Initialize clients
    tripc_client = TripCAPIClient()
    llm_client = RateLimitedLLMClient(OpenAIClient())
    service_agent = ServiceAgent(tripc_client, llm_client)
    
    # Test queries
    test_queries = [
        {
            "query": "Tìm nhà hàng ngon",
            "description": "General restaurant query",
            "should_mention_culinary": True
        },
        {
            "query": "Quán ăn ở Đà Nẵng",
            "description": "Restaurant in specific city",
            "should_mention_culinary": True
        },
        {
            "query": "Nhà hàng hải sản",
            "description": "Seafood restaurant",
            "should_mention_culinary": True
        },
        {
            "query": "Quán cafe",
            "description": "Cafe query",
            "should_mention_culinary": False
        }
    ]
    
    platform_context = PlatformContext(
        platform=PlatformType.MOBILE_APP,
        device=DeviceType.ANDROID,
        language=LanguageType.VIETNAMESE
    )
    
    results = []
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📋 Test {i}: {test_case['description']}")
        print(f"Query: '{test_case['query']}'")
        print("-" * 50)
        
        try:
            # Get services response
            response = await service_agent.get_services(
                test_case['query'], platform_context
            )
            
            answer_ai = response.answerAI
            print(f"🤖 AI Response: {answer_ai}")
            
            # Check if culinary passport is mentioned
            culinary_keywords = ["hộ chiếu ẩm thực", "chứng nhận chất lượng", "culinary passport"]
            has_culinary_mention = any(keyword in answer_ai.lower() for keyword in culinary_keywords)
            
            if test_case['should_mention_culinary']:
                if has_culinary_mention:
                    print(f"✅ PASS: Restaurant query mentions culinary passport")
                    results.append(True)
                else:
                    print(f"❌ FAIL: Restaurant query should mention culinary passport")
                    results.append(False)
            else:
                if has_culinary_mention:
                    print(f"❌ FAIL: Non-restaurant query should not mention culinary passport")
                    results.append(False)
                else:
                    print(f"✅ PASS: Non-restaurant query correctly doesn't mention culinary passport")
                    results.append(True)
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append(False)
    
    # Summary
    print(f"\n📊 SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Culinary passport prompts are working correctly.")
    else:
        print("⚠️  Some tests failed. Check prompt logic.")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_culinary_passport_prompt())

