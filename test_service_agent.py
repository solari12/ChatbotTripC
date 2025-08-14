#!/usr/bin/env python3
"""
Test script để kiểm tra ServiceAgent với KeywordAnalyzer
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

from app.agents.service_agent import ServiceAgent
from app.services.tripc_api import TripCAPIClient
from app.llm.open_client import OpenAIClient
from app.core.platform_context import PlatformContext

async def test_service_agent():
    """Test ServiceAgent với KeywordAnalyzer"""
    
    print("🔍 Testing ServiceAgent with KeywordAnalyzer...")
    
    # Initialize clients
    llm_client = OpenAIClient()
    tripc_client = TripCAPIClient()
    
    # Initialize ServiceAgent
    service_agent = ServiceAgent(tripc_client, llm_client)
    
    # Create platform context
    platform_context = PlatformContext(
        platform="web_browser",
        device="android",
        language="vi"
    )
    
    # Test query
    query = "Gợi ý nhà hàng hàn quốc"
    
    try:
        print(f"📝 Query: {query}")
        
        # Get services
        service_response = await service_agent.get_services(
            query=query,
            platform_context=platform_context,
            service_type="restaurant"
        )
        
        print(f"📊 Service Response:")
        print(f"Type: {service_response.type}")
        print(f"AnswerAI: {service_response.answerAI}")
        print(f"Total Services: {len(service_response.services)}")
        
        # Show services
        if service_response.services:
            print("🏪 Services found:")
            for j, service in enumerate(service_response.services, 1):
                print(f"  {j}. {service.name}")
                print(f"     Address: {service.address}")
                print(f"     City: {service.city}")
                print(f"     Product Types: {service.productTypes}")
                print()
        else:
            print("❌ No services found")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Starting ServiceAgent Tests...")
    
    # Test ServiceAgent
    asyncio.run(test_service_agent())
    
    print("\n✅ ServiceAgent tests completed!")



