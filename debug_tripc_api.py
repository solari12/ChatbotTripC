#!/usr/bin/env python3
"""
Debug TripC API directly
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.services.tripc_api import TripCAPIClient

async def debug_tripc_api():
    """Debug TripC API responses"""
    print("🔍 Debugging TripC API")
    print("=" * 50)
    
    client = TripCAPIClient()
    
    # Test 1: Get all restaurants (no filters)
    print("\n1️⃣ Testing: Get all restaurants (no filters)")
    restaurants = await client.get_restaurants(page=1, page_size=5)
    print(f"   Found: {len(restaurants)} restaurants")
    if restaurants:
        print(f"   First restaurant: {restaurants[0].name}")
        print(f"   Product types: {restaurants[0].productTypes}")
    
    # Test 2: Search by city only
    print("\n2️⃣ Testing: Search by city (Đà Nẵng)")
    restaurants = await client.get_restaurants(page=1, page_size=5, city="Đà Nẵng")
    print(f"   Found: {len(restaurants)} restaurants in Đà Nẵng")
    if restaurants:
        print(f"   First restaurant: {restaurants[0].name}")
        print(f"   Product types: {restaurants[0].productTypes}")
    
    # Test 3: Search by keyword only
    print("\n3️⃣ Testing: Search by keyword (hải sản)")
    restaurants = await client.get_restaurants(page=1, page_size=5, keyword="hải sản")
    print(f"   Found: {len(restaurants)} restaurants with 'hải sản'")
    if restaurants:
        print(f"   First restaurant: {restaurants[0].name}")
        print(f"   Product types: {restaurants[0].productTypes}")
    
    # Test 4: Search by different keywords
    print("\n4️⃣ Testing: Search by different keywords")
    keywords = ["việt nam", "chinese", "korean", "japanese", "italian"]
    for keyword in keywords:
        restaurants = await client.get_restaurants(page=1, page_size=3, keyword=keyword)
        print(f"   '{keyword}': {len(restaurants)} restaurants")
        if restaurants:
            print(f"     First: {restaurants[0].name} ({restaurants[0].productTypes})")
    
    # Test 5: Check what product types exist
    print("\n5️⃣ Testing: Check existing product types")
    all_restaurants = await client.get_restaurants(page=1, page_size=20)
    product_types = set()
    for restaurant in all_restaurants:
        if restaurant.productTypes:
            product_types.add(restaurant.productTypes)
    
    print(f"   Available product types: {list(product_types)}")
    
    # Test 6: Test combined keyword search
    print("\n6️⃣ Testing: Combined keyword search (hải sản Đà Nẵng)")
    restaurants = await client.get_restaurants(page=1, page_size=5, keyword="hải sản", city="Đà Nẵng")
    print(f"   Found: {len(restaurants)} restaurants with 'hải sản Đà Nẵng'")
    if restaurants:
        print(f"   First restaurant: {restaurants[0].name}")
        print(f"   Product types: {restaurants[0].productTypes}")
        print(f"   City: {restaurants[0].city}")
    
    # Test 7: Check seafood restaurant details
    print("\n7️⃣ Testing: Check seafood restaurant details")
    seafood_restaurants = await client.get_restaurants(page=1, page_size=10, keyword="hải sản")
    for restaurant in seafood_restaurants:
        print(f"   Restaurant: {restaurant.name}")
        print(f"   City: {restaurant.city}")
        print(f"   Address: {restaurant.address}")
        print(f"   Product types: {restaurant.productTypes}")
        print()
    
    await client.client.aclose()

if __name__ == "__main__":
    asyncio.run(debug_tripc_api())
