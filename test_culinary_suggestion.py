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

async def test_culinary_passport_suggestion():
    """Test culinary passport suggestion for restaurant queries"""
    
    print("🎯 TESTING CULINARY PASSPORT SUGGESTION")
    print("=" * 60)
    
    # Initialize clients
    tripc_client = TripCAPIClient()
    llm_client = RateLimitedLLMClient(OpenAIClient())
    service_agent = ServiceAgent(tripc_client, llm_client)
    
    # Test queries
    test_queries = [
        {
            "query": "Tìm nhà hàng ngon",
            "description": "General restaurant query"
        },
        {
            "query": "Quán ăn ở Đà Nẵng",
            "description": "Restaurant in specific city"
        },
        {
            "query": "Nhà hàng hải sản",
            "description": "Seafood restaurant"
        },
        {
            "query": "Quán cafe",
            "description": "Cafe query (should not have culinary passport)"
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
            
            # Check suggestions
            suggestions = response.suggestions
            culinary_suggestion = None
            
            print(f"🔍 Suggestions found: {len(suggestions)}")
            for j, suggestion in enumerate(suggestions, 1):
                print(f"  {j}. {suggestion.label} - {suggestion.action}")
                if suggestion.action == "show_culinary_passport":
                    culinary_suggestion = suggestion
            
            # Check if culinary passport suggestion is present for restaurant queries
            if "cafe" in test_case['query'].lower():
                # Cafe queries should NOT have culinary passport suggestion
                if culinary_suggestion:
                    print(f"❌ FAIL: Cafe query should not have culinary passport suggestion")
                    results.append(False)
                else:
                    print(f"✅ PASS: Cafe query correctly has no culinary passport suggestion")
                    results.append(True)
            else:
                # Restaurant queries SHOULD have culinary passport suggestion
                if culinary_suggestion:
                    print(f"✅ PASS: Restaurant query has culinary passport suggestion")
                    print(f"     Label: {culinary_suggestion.label}")
                    print(f"     Detail: {culinary_suggestion.detail}")
                    results.append(True)
                else:
                    print(f"❌ FAIL: Restaurant query should have culinary passport suggestion")
                    results.append(False)
                
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
        print("🎉 ALL TESTS PASSED! Culinary passport suggestions are working correctly.")
    else:
        print("⚠️  Some tests failed. Check suggestion logic.")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_culinary_passport_suggestion())

