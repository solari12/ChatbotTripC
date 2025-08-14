#!/usr/bin/env python3
"""
Test script để kiểm tra province_ids cho Đà Nẵng
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

async def test_province_ids():
    """Test các province_id để tìm province_id đúng cho Đà Nẵng"""
    
    print("🔍 Testing Province IDs for Đà Nẵng...")
    
    # Initialize clients
    llm_client = OpenAIClient()
    tripc_client = TripCAPIClient()
    
    # Initialize KeywordAnalyzer
    analyzer = KeywordAnalyzer(llm_client, tripc_client)
    
    try:
        # Test province IDs
        test_result = await analyzer.test_province_ids()
        
        print("📊 Province ID Test Results:")
        print(json.dumps(test_result, indent=2, ensure_ascii=False))
        
        # Tìm province_id tốt nhất
        best_province_id = None
        best_danang_count = 0
        
        for province_id, result in test_result.items():
            if "error" not in result:
                danang_count = result.get("danang_count", 0)
                if danang_count > best_danang_count:
                    best_danang_count = danang_count
                    best_province_id = province_id
        
        print(f"\n🏆 Best Province ID for Đà Nẵng: {best_province_id}")
        print(f"📈 Đà Nẵng restaurants found: {best_danang_count}")
        
        if best_province_id:
            print(f"📋 Sample restaurants from province_id {best_province_id}:")
            sample_restaurants = test_result[best_province_id].get("sample_restaurants", [])
            for i, restaurant in enumerate(sample_restaurants, 1):
                print(f"  {i}. {restaurant}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_specific_province():
    """Test một province_id cụ thể"""
    
    print("\n🔍 Testing Specific Province ID...")
    
    # Initialize clients
    llm_client = OpenAIClient()
    tripc_client = TripCAPIClient()
    
    # Initialize KeywordAnalyzer
    analyzer = KeywordAnalyzer(llm_client, tripc_client)
    
    # Test với province_id = 1 (có thể là Đà Nẵng)
    province_id = 1
    product_type_id = 23  # Ẩm thực Hàn
    
    try:
        restaurant_batch = await tripc_client.get_restaurants(
            page=1,
            page_size=10,
            product_type_id=product_type_id,
            province_id=province_id
        )
        
        print(f"📊 Results for province_id={province_id}, product_type_id={product_type_id}:")
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
    print("🧪 Starting Province ID Tests...")
    
    # Test province IDs
    asyncio.run(test_province_ids())
    
    # Test specific province
    asyncio.run(test_specific_province())
    
    print("\n✅ Province ID tests completed!")



