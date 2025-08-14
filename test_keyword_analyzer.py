#!/usr/bin/env python3
"""
Test script for KeywordAnalyzer functionality
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

async def test_keyword_analyzer():
    """Test the KeywordAnalyzer functionality"""
    
    print("🚀 Testing KeywordAnalyzer...")
    
    # Initialize clients
    llm_client = OpenAIClient()
    tripc_client = TripCAPIClient()
    
    # Initialize KeywordAnalyzer
    analyzer = KeywordAnalyzer(llm_client, tripc_client)
    
    # Test queries
    test_queries = [
        "Tôi muốn tìm nhà hàng hải sản ở Đà Nẵng",
        "Có nhà hàng buffet nào ngon không?",
        "Tìm quán cà phê view đẹp",
        "Nhà hàng chay ở đâu?",
        "Quán ăn vặt đường phố"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {query}")
        print("-" * 50)
        
        try:
            # Test keyword analysis
            print("🔍 Analyzing keywords...")
            analysis_result = await analyzer.process_user_query(query)
            
            print("📊 Analysis Result:")
            print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
            
            # Test restaurant search
            print("\n🍽️ Searching restaurants...")
            search_result = await analyzer.search_restaurants_with_analysis(
                user_query=query,
                page=1,
                page_size=5
            )
            
            print(f"📈 Found {search_result['total_found']} restaurants")
            
            # Show first few restaurants
            for j, restaurant in enumerate(search_result['restaurants'][:3], 1):
                print(f"  {j}. {restaurant.name} - {restaurant.address}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "="*60)

async def test_product_types():
    """Test getting all product types"""
    
    print("🔍 Testing Product Types API...")
    
    # Initialize clients
    llm_client = OpenAIClient()
    tripc_client = TripCAPIClient()
    
    # Initialize KeywordAnalyzer
    analyzer = KeywordAnalyzer(llm_client, tripc_client)
    
    try:
        product_types = await analyzer.get_all_product_types()
        print(f"📊 Found {len(product_types)} product types")
        
        # Show first 10 product types
        print("\n📋 First 10 Product Types:")
        for i, pt in enumerate(product_types[:10], 1):
            print(f"  {i}. ID: {pt.get('id')} - Name: {pt.get('name')} - Slug: {pt.get('slug')}")
        
        # Save to file for reference
        with open('product_types.json', 'w', encoding='utf-8') as f:
            json.dump(product_types, f, indent=2, ensure_ascii=False)
        print("\n💾 Product types saved to product_types.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Starting KeywordAnalyzer Tests...")
    
    # Test product types first
    asyncio.run(test_product_types())
    
    # Test keyword analyzer
    asyncio.run(test_keyword_analyzer())
    
    print("\n✅ Tests completed!")



