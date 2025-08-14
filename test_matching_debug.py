#!/usr/bin/env python3
"""
Test script để debug vấn đề matching product types
"""

import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
import sys
sys.path.append('src')

from app.services.keyword_analyzer import KeywordAnalyzer
from app.services.tripc_api import TripCAPIClient
from app.llm.open_client import OpenAIClient

async def test_specific_queries():
    """Test các câu hỏi cụ thể để debug"""
    
    print("🔍 Testing Specific Queries for Debug...")
    
    # Initialize clients
    llm_client = OpenAIClient()
    tripc_client = TripCAPIClient()
    
    # Initialize KeywordAnalyzer
    analyzer = KeywordAnalyzer(llm_client, tripc_client)
    
    # Test queries có vấn đề
    test_queries = [
        "Gợi ý nhà hàng hàn quốc",
        "Tìm nhà hàng chả cá",
        "Nhà hàng BBQ Hàn Quốc",
        "Quán ăn hải sản",
        "Nhà hàng Việt Nam"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"📝 Test {i}: {query}")
        print(f"{'='*60}")
        
        try:
            # Debug matching
            print("🔍 Debugging matching process...")
            debug_result = await analyzer.debug_matching(query)
            
            print("📊 Debug Result:")
            print(json.dumps(debug_result, indent=2, ensure_ascii=False))
            
            # Test restaurant search
            print("\n🍽️ Testing restaurant search...")
            search_result = await analyzer.search_restaurants_with_analysis(
                user_query=query,
                page=1,
                page_size=5
            )
            
            print(f"📈 Found {search_result['total_found']} restaurants")
            
            # Show first few restaurants
            if search_result['restaurants']:
                print("🏪 Restaurants found:")
                for j, restaurant in enumerate(search_result['restaurants'][:3], 1):
                    print(f"  {j}. {restaurant.name} - {restaurant.address}")
                    if hasattr(restaurant, 'productTypes'):
                        print(f"     Product Types: {restaurant.productTypes}")
            else:
                print("❌ No restaurants found")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()

async def test_product_types():
    """Test lấy product types"""
    
    print("🔍 Testing Product Types...")
    
    # Initialize clients
    llm_client = OpenAIClient()
    tripc_client = TripCAPIClient()
    
    # Initialize KeywordAnalyzer
    analyzer = KeywordAnalyzer(llm_client, tripc_client)
    
    try:
        product_types = await analyzer.get_all_product_types()
        print(f"📊 Found {len(product_types)} product types")
        
        # Show all product types
        print("\n📋 All Product Types:")
        for i, pt in enumerate(product_types, 1):
            print(f"  {i:2d}. ID: {pt.get('id'):2d} - Name: {pt.get('name')} - Slug: {pt.get('slug')}")
        
        # Save to file
        with open('all_product_types.json', 'w', encoding='utf-8') as f:
            json.dump(product_types, f, indent=2, ensure_ascii=False)
        print("\n💾 All product types saved to all_product_types.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Starting Matching Debug Tests...")
    
    # Test product types first
    asyncio.run(test_product_types())
    
    # Test specific queries
    asyncio.run(test_specific_queries())
    
    print("\n✅ Debug tests completed!")



