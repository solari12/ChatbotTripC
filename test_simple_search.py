#!/usr/bin/env python3
"""
Test script đơn giản để kiểm tra tìm kiếm nhà hàng Hàn Quốc
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

async def test_korean_restaurants():
    """Test tìm kiếm nhà hàng Hàn Quốc"""
    
    print("🔍 Testing Korean Restaurant Search...")
    
    # Initialize clients
    llm_client = OpenAIClient()
    tripc_client = TripCAPIClient()
    
    # Initialize KeywordAnalyzer
    analyzer = KeywordAnalyzer(llm_client, tripc_client)
    
    # Test query
    query = "Gợi ý nhà hàng hàn quốc"
    
    try:
        print(f"📝 Query: {query}")
        
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
            page_size=10
        )
        
        print(f"📈 Found {search_result['total_found']} restaurants")
        
        # Show restaurants
        if search_result['restaurants']:
            print("🏪 Restaurants found:")
            for j, restaurant in enumerate(search_result['restaurants'], 1):
                print(f"  {j}. {restaurant.name}")
                print(f"     Address: {restaurant.address}")
                print(f"     City: {restaurant.city}")
                print(f"     Product Types: {restaurant.productTypes}")
                print()
        else:
            print("❌ No restaurants found")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_direct_api():
    """Test trực tiếp API với product_type_id=74"""
    
    print("\n🔍 Testing Direct API Call...")
    
    # Initialize clients
    tripc_client = TripCAPIClient()
    
    try:
        # Test trực tiếp với product_type_id=74 (BBQ Hàn Quốc)
        restaurant_batch = await tripc_client.get_restaurants(
            page=1,
            page_size=10,
            product_type_id=74
        )
        
        print(f"📊 Direct API Results for product_type_id=74:")
        print(f"Total restaurants: {len(restaurant_batch)}")
        
        for i, restaurant in enumerate(restaurant_batch, 1):
            print(f"  {i}. {restaurant.name}")
            print(f"     Address: {restaurant.address}")
            print(f"     City: {restaurant.city}")
            print(f"     Product Types: {restaurant.productTypes}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Starting Simple Search Tests...")
    
    # Test Korean restaurants
    asyncio.run(test_korean_restaurants())
    
    # Test direct API
    asyncio.run(test_direct_api())
    
    print("\n✅ Simple search tests completed!")



