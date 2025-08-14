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

async def test_llm_product_type_extraction():
    """Test LLM product type ID extraction"""
    
    print("🎯 TESTING LLM PRODUCT TYPE ID EXTRACTION")
    print("=" * 60)
    
    # Initialize clients
    tripc_client = TripCAPIClient()
    llm_client = RateLimitedLLMClient(OpenAIClient())
    service_agent = ServiceAgent(tripc_client, llm_client)
    
    # Test queries
    test_queries = [
        {
            "query": "Tìm quán nhậu",
            "expected_product_type_id": 22,
            "description": "Quán nhậu/Craft beer"
        },
        {
            "query": "Tìm quán bún",
            "expected_product_type_id": 77,
            "description": "Bún/Phở"
        },
        {
            "query": "Nhà hàng hải sản",
            "expected_product_type_id": 93,
            "description": "Hải sản"
        },
        {
            "query": "Quán cafe view đẹp",
            "expected_product_type_id": 8,
            "description": "Cafe"
        },
        {
            "query": "Nhà hàng Nhật",
            "expected_product_type_id": 62,
            "description": "Ẩm thực Nhật"
        },
        {
            "query": "Quán lẩu nướng",
            "expected_product_type_id": 20,
            "description": "Lẩu nướng"
        },
        {
            "query": "Tìm quán trà sữa",
            "expected_product_type_id": 12,
            "description": "Trà sữa"
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
        print(f"Expected Product Type ID: {test_case['expected_product_type_id']}")
        print("-" * 50)
        
        try:
            # Extract search parameters using LLM
            search_params = await service_agent._extract_search_params_with_llm(
                test_case['query'], platform_context
            )
            
            actual_product_type_id = search_params.get("product_type_id")
            keyword = search_params.get("keyword", "")
            city = search_params.get("city", "")
            
            print(f"🔍 Extracted Parameters:")
            print(f"  - Product Type ID: {actual_product_type_id}")
            print(f"  - Keyword: '{keyword}'")
            print(f"  - City: '{city}'")
            
            # Check if product_type_id matches expected
            if actual_product_type_id == test_case['expected_product_type_id']:
                print(f"✅ PASS: Product Type ID matches expected ({actual_product_type_id})")
                results.append(True)
            else:
                print(f"❌ FAIL: Expected {test_case['expected_product_type_id']}, got {actual_product_type_id}")
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
        print("🎉 ALL TESTS PASSED! LLM product type extraction is working correctly.")
    else:
        print("⚠️  Some tests failed. Check LLM responses and product type mapping.")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_llm_product_type_extraction())

