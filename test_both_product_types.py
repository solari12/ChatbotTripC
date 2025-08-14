#!/usr/bin/env python3
"""
Test script để kiểm tra cả 2 product_type_id
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

from app.services.tripc_api import TripCAPIClient

async def test_both_product_types():
    """Test cả 2 product_type_id"""
    
    print("🔍 Testing Both Product Type IDs...")
    
    # Initialize client
    tripc_client = TripCAPIClient()
    
    # Test product_type_id = 23 (Ẩm thực Hàn)
    print("\n🍽️ Testing product_type_id = 23 (Ẩm thực Hàn):")
    try:
        restaurants_23 = await tripc_client.get_restaurants(
            page=1,
            page_size=10,
            product_type_id=23
        )
        
        print(f"📊 Results for product_type_id=23:")
        print(f"Total restaurants: {len(restaurants_23)}")
        
        for i, restaurant in enumerate(restaurants_23, 1):
            print(f"  {i}. {restaurant.name}")
            print(f"     Address: {restaurant.address}")
            print(f"     City: {restaurant.city}")
            print(f"     Product Types: {restaurant.productTypes}")
            print()
            
    except Exception as e:
        print(f"❌ Error with product_type_id=23: {e}")
    
    # Test product_type_id = 74 (BBQ Hàn Quốc)
    print("\n🍽️ Testing product_type_id = 74 (BBQ Hàn Quốc):")
    try:
        restaurants_74 = await tripc_client.get_restaurants(
            page=1,
            page_size=10,
            product_type_id=74
        )
        
        print(f"📊 Results for product_type_id=74:")
        print(f"Total restaurants: {len(restaurants_74)}")
        
        for i, restaurant in enumerate(restaurants_74, 1):
            print(f"  {i}. {restaurant.name}")
            print(f"     Address: {restaurant.address}")
            print(f"     City: {restaurant.city}")
            print(f"     Product Types: {restaurant.productTypes}")
            print()
            
    except Exception as e:
        print(f"❌ Error with product_type_id=74: {e}")

if __name__ == "__main__":
    print("🧪 Starting Both Product Types Tests...")
    
    # Test both product types
    asyncio.run(test_both_product_types())
    
    print("\n✅ Both product types tests completed!")



