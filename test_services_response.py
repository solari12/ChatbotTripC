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

async def test_services_response():
    """Test services response to check if all required fields are present"""
    
    print("🔍 TESTING SERVICES RESPONSE COMPLETENESS")
    print("=" * 60)
    
    # Create TripC API client and Service Agent
    tripc_client = TripCAPIClient()
    service_agent = ServiceAgent(tripc_client)
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Restaurant Services (Vietnamese)",
            "query": "Tìm nhà hàng ngon ở Đà Nẵng",
            "platform": PlatformType.WEB_BROWSER,
            "device": DeviceType.DESKTOP,
            "language": LanguageType.VIETNAMESE,
            "service_type": "restaurant"
        },
        {
            "name": "Restaurant Services (English)",
            "query": "Find good restaurants in Da Nang",
            "platform": PlatformType.MOBILE_APP,
            "device": DeviceType.ANDROID,
            "language": LanguageType.ENGLISH,
            "service_type": "restaurant"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📋 Test {i}: {scenario['name']}")
        print(f"Query: {scenario['query']}")
        print(f"Platform: {scenario['platform'].value}, Device: {scenario['device'].value}")
        print(f"Language: {scenario['language'].value}")
        print("-" * 50)
        
        try:
            platform_context = PlatformContext(
                platform=scenario['platform'],
                device=scenario['device'],
                language=scenario['language']
            )
            
            # Get services response
            response = await service_agent.get_services(
                scenario['query'], 
                platform_context, 
                scenario['service_type']
            )
            
            print(f"🤖 Answer: {response.answerAI[:100]}...")
            print(f"📊 Services found: {len(response.services)}")
            
            # Check each service for required fields
            if response.services:
                print(f"\n🔍 Analyzing first service:")
                first_service = response.services[0]
                
                # Required fields according to API documentation
                required_fields = [
                    "id", "name", "type", "imageUrl", "coverImageUrl", 
                    "rating", "totalReviews", "address", "city", 
                    "productTypes", "description", "priceRange", 
                    "workingHoursDisplay", "amenities", "location"
                ]
                
                missing_fields = []
                present_fields = []
                
                for field in required_fields:
                    value = getattr(first_service, field, None)
                    if value is not None:
                        present_fields.append(field)
                        if field in ["imageUrl", "coverImageUrl", "description", "address"]:
                            print(f"  ✅ {field}: {str(value)[:50]}...")
                        elif field == "amenities" and isinstance(value, list):
                            print(f"  ✅ {field}: {value[:3]}...")
                        elif field == "location" and isinstance(value, dict):
                            print(f"  ✅ {field}: {value}")
                        else:
                            print(f"  ✅ {field}: {value}")
                    else:
                        missing_fields.append(field)
                        print(f"  ❌ {field}: MISSING")
                
                print(f"\n📊 Field Analysis:")
                print(f"  ✅ Present: {len(present_fields)}/{len(required_fields)} fields")
                print(f"  ❌ Missing: {len(missing_fields)} fields")
                
                if missing_fields:
                    print(f"  Missing fields: {missing_fields}")
                
                # Calculate completeness score
                completeness_score = len(present_fields) / len(required_fields)
                print(f"  📈 Completeness: {completeness_score:.1%}")
                
                if completeness_score >= 0.8:
                    print("  🎉 EXCELLENT: Services response is complete!")
                elif completeness_score >= 0.6:
                    print("  ✅ GOOD: Services response is mostly complete")
                else:
                    print("  ⚠️  NEEDS IMPROVEMENT: Services response is incomplete")
                
                # Check suggestions
                print(f"\n💡 Suggestions: {len(response.suggestions)}")
                for j, suggestion in enumerate(response.suggestions, 1):
                    print(f"  {j}. {suggestion.label} - {suggestion.action}")
                
                # Check sources
                print(f"\n📚 Sources: {len(response.sources)}")
                for j, source in enumerate(response.sources, 1):
                    print(f"  {j}. {source.title}")
                
            else:
                print("❌ No services found in response")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("🎯 SERVICES RESPONSE TEST COMPLETED")
    print(f"{'='*60}")

if __name__ == "__main__":
    print("Starting services response test...")
    asyncio.run(test_services_response())
    print("\n�� Test completed!")
