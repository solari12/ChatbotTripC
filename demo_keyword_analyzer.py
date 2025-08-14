#!/usr/bin/env python3
"""
Demo script for KeywordAnalyzer functionality
"""

import asyncio
import json
import requests
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_keyword_analysis():
    """Test keyword analysis endpoint"""
    
    print("🔍 Testing Keyword Analysis API...")
    print("=" * 60)
    
    test_queries = [
        "Tôi muốn tìm nhà hàng hải sản ở Đà Nẵng",
        "Có nhà hàng buffet nào ngon không?",
        "Tìm quán cà phê view đẹp",
        "Nhà hàng chay ở đâu?",
        "Quán ăn vặt đường phố"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {query}")
        print("-" * 40)
        
        try:
            # Call keyword analysis API
            response = requests.post(
                f"{BASE_URL}/api/v1/keywords/analyze",
                json={"query": query},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                analysis = data["data"]
                
                print("✅ Analysis Result:")
                print(f"  Keywords: {analysis['keywords']}")
                print(f"  Product Type IDs: {analysis['matching_product_type_ids']}")
                print(f"  Province IDs: {analysis['province_ids']}")
                print(f"  Total Product Types: {analysis['total_product_types']}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()

def test_restaurant_search():
    """Test restaurant search with analysis endpoint"""
    
    print("🍽️ Testing Restaurant Search with Analysis API...")
    print("=" * 60)
    
    test_queries = [
        "Tôi muốn tìm nhà hàng hải sản ở Đà Nẵng",
        "Có nhà hàng buffet nào ngon không?",
        "Tìm quán cà phê view đẹp"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {query}")
        print("-" * 40)
        
        try:
            # Call restaurant search API
            response = requests.post(
                f"{BASE_URL}/api/v1/restaurants/search-with-analysis",
                json={
                    "query": query,
                    "page": 1,
                    "page_size": 5
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data["data"]
                
                print("✅ Search Result:")
                print(f"  Total Found: {result['total_found']}")
                print(f"  Analysis: {result['analysis']['keywords']}")
                print(f"  Product Type IDs: {result['analysis']['matching_product_type_ids']}")
                
                # Show first few restaurants
                if result['restaurants']:
                    print("  Restaurants:")
                    for j, restaurant in enumerate(result['restaurants'][:3], 1):
                        print(f"    {j}. {restaurant['name']} - {restaurant['address']}")
                else:
                    print("  No restaurants found")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()

def test_health_check():
    """Test health check endpoint"""
    
    print("🏥 Testing Health Check...")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Health Check Result:")
            print(f"  Status: {data['status']}")
            print(f"  Service: {data['service']}")
            print(f"  Timestamp: {data['timestamp']}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    """Main demo function"""
    
    print("🚀 TripC.AI Keyword Analyzer Demo")
    print("=" * 60)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 API Base URL: {BASE_URL}")
    print()
    
    # Test health check first
    test_health_check()
    print()
    
    # Test keyword analysis
    test_keyword_analysis()
    print()
    
    # Test restaurant search
    test_restaurant_search()
    print()
    
    print("✅ Demo completed!")

if __name__ == "__main__":
    main()



