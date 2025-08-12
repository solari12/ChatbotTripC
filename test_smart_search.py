import asyncio
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from app.agents.service_agent import ServiceAgent
    from app.services.tripc_api import TripCAPIClient
    from app.models.platform_models import PlatformContext, LanguageType, PlatformType, DeviceType
    print("Imports successful")
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)

async def test_smart_search():
    """Test smart search functionality of Service Agent"""
    
    print("🔍 TESTING SMART SEARCH FUNCTIONALITY")
    print("=" * 60)
    
    # Create TripC API client and Service Agent
    tripc_client = TripCAPIClient()
    service_agent = ServiceAgent(tripc_client)
    
    # Test scenarios with different search queries
    test_scenarios = [
        {
            "name": "Location-based Search",
            "query": "Nhà hàng ngon ở Đà Nẵng",
            "expected_criteria": {"location": "đà nẵng", "rating": "high"},
            "description": "Should extract location and quality preference"
        },
        {
            "name": "Cuisine-based Search",
            "query": "Tìm nhà hàng hải sản",
            "expected_criteria": {"cuisine": "seafood"},
            "description": "Should extract cuisine type"
        },
        {
            "name": "Price-based Search",
            "query": "Nhà hàng rẻ ở Hội An",
            "expected_criteria": {"location": "hội an", "price_range": "low"},
            "description": "Should extract location and price preference"
        },
        {
            "name": "Complex Search",
            "query": "Nhà hàng Việt Nam ngon và rẻ ở Sài Gòn",
            "expected_criteria": {"location": "sài gòn", "cuisine": "vietnamese", "rating": "high", "price_range": "low"},
            "description": "Should extract multiple criteria"
        },
        {
            "name": "English Search",
            "query": "Find good seafood restaurants in Da Nang",
            "expected_criteria": {"location": "da nang", "cuisine": "seafood", "rating": "high"},
            "description": "Should work with English queries"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📋 Test {i}: {scenario['name']}")
        print(f"Query: {scenario['query']}")
        print(f"Expected: {scenario['expected_criteria']}")
        print(f"Description: {scenario['description']}")
        print("-" * 50)
        
        try:
            # Test search criteria extraction
            extracted_criteria = service_agent._extract_search_criteria(scenario['query'])
            print(f"🔍 Extracted criteria: {extracted_criteria}")
            
            # Test optimized query building
            optimized_query = service_agent._build_search_query(scenario['query'], extracted_criteria)
            print(f"🔧 Optimized query: {optimized_query}")
            
            # Check if criteria match expectations
            expected = scenario['expected_criteria']
            matches = 0
            total_expected = len(expected)
            
            for key, value in expected.items():
                if key in extracted_criteria and extracted_criteria[key] == value:
                    matches += 1
                    print(f"  ✅ {key}: {value} - MATCH")
                else:
                    actual = extracted_criteria.get(key, "NOT FOUND")
                    print(f"  ❌ {key}: expected {value}, got {actual}")
            
            accuracy = matches / total_expected if total_expected > 0 else 1.0
            print(f"\n📊 Criteria Accuracy: {accuracy:.1%} ({matches}/{total_expected})")
            
            if accuracy >= 0.8:
                print("  🎉 EXCELLENT: Search criteria extraction working well!")
            elif accuracy >= 0.6:
                print("  ✅ GOOD: Search criteria extraction mostly working")
            else:
                print("  ⚠️  NEEDS IMPROVEMENT: Search criteria extraction needs work")
            
            # Test full service search (if we have API access)
            print(f"\n🚀 Testing full service search...")
            platform_context = PlatformContext(
                platform=PlatformType.WEB_BROWSER,
                device=DeviceType.DESKTOP,
                language=LanguageType.VIETNAMESE
            )
            
            response = await service_agent.get_services(
                scenario['query'], 
                platform_context, 
                "restaurant"
            )
            
            print(f"🤖 Answer: {response.answerAI[:100]}...")
            print(f"📊 Services found: {len(response.services)}")
            
            if response.services:
                print(f"🍽️  First service: {response.services[0].name}")
                if response.services[0].city:
                    print(f"📍 Location: {response.services[0].city}")
                if response.services[0].productTypes:
                    print(f"🍜 Cuisine: {response.services[0].productTypes}")
            
            print(f"💡 Suggestions: {len(response.suggestions)}")
            for j, suggestion in enumerate(response.suggestions, 1):
                print(f"  {j}. {suggestion.label} - {suggestion.action}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("🎯 SMART SEARCH TEST COMPLETED")
    print(f"{'='*60}")

if __name__ == "__main__":
    print("Starting smart search test...")
    asyncio.run(test_smart_search())
    print("\n�� Test completed!")
