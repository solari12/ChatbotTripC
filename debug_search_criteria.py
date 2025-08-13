#!/usr/bin/env python3
"""
Debug search criteria extraction
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.agents.service_agent import ServiceAgent
from app.services.tripc_api import TripCAPIClient

def debug_search_criteria():
    """Debug search criteria extraction"""
    print("🔍 Debugging Search Criteria Extraction")
    print("=" * 50)
    
    client = TripCAPIClient()
    agent = ServiceAgent(client)
    
    # Test query
    query = "Tìm nhà hàng hải sản ở Đà Nẵng"
    print(f"Query: {query}")
    
    # Extract search criteria
    criteria = agent._extract_search_criteria(query)
    print(f"Extracted criteria: {criteria}")
    
    # Check what would be used for search
    location = criteria.get("location")
    cuisine = criteria.get("cuisine")
    
    print(f"Location: {location}")
    print(f"Cuisine: {cuisine}")
    
    # Simulate the search logic
    if location:
        print(f"\nWould search by location: {location}")
        # This would be the actual API call
        import asyncio
        
        async def test_search():
            # Get restaurants by location
            services = await client.get_restaurants(page=1, page_size=20, city=location)
            print(f"Found {len(services)} restaurants in {location}")
            
            if services:
                print("First few restaurants:")
                for i, service in enumerate(services[:3]):
                    print(f"  {i+1}. {service.name} - {service.city}")
                    print(f"     Product types: {service.productTypes}")
                
                # Test filtering
                if cuisine:
                    print(f"\nFiltering by cuisine: {cuisine}")
                    cuisine_filter = cuisine.lower()
                    filtered_services = []
                    for service in services:
                        service_text = f"{service.name} {service.description} {service.productTypes}".lower()
                        if cuisine_filter in service_text:
                            filtered_services.append(service)
                            print(f"  ✅ Match: {service.name}")
                        else:
                            print(f"  ❌ No match: {service.name} (text: {service_text[:50]}...)")
                    
                    print(f"Filtered results: {len(filtered_services)} restaurants")
            
            # Also check all restaurants to see if seafood restaurant exists
            print(f"\nChecking all restaurants for '{cuisine}'...")
            all_services = await client.get_restaurants(page=1, page_size=50)
            seafood_services = []
            for service in all_services:
                service_text = f"{service.name} {service.description} {service.productTypes}".lower()
                if cuisine_filter in service_text:
                    seafood_services.append(service)
                    print(f"  Found: {service.name} - {service.city}")
            
            print(f"Total seafood restaurants found: {len(seafood_services)}")
            
            # Check multiple pages for Đà Nẵng
            print(f"\nChecking multiple pages for Đà Nẵng restaurants...")
            all_danang_services = []
            for p in range(1, 4):
                page_services = await client.get_restaurants(page=p, page_size=20, city="Đà Nẵng")
                print(f"Page {p}: {len(page_services)} restaurants")
                all_danang_services.extend(page_services)
                if len(page_services) < 20:
                    break
            
            print(f"Total Đà Nẵng restaurants across pages: {len(all_danang_services)}")
            
            # Check for seafood in all Đà Nẵng restaurants
            seafood_in_danang = []
            for service in all_danang_services:
                service_text = f"{service.name} {service.description} {service.productTypes}".lower()
                if cuisine_filter in service_text:
                    seafood_in_danang.append(service)
                    print(f"  Found in Đà Nẵng: {service.name}")
            
            print(f"Seafood restaurants in Đà Nẵng: {len(seafood_in_danang)}")
            
            await client.client.aclose()
        
        asyncio.run(test_search())
    elif cuisine:
        print(f"\nWould search by cuisine: {cuisine}")
        # This would be the actual API call
    else:
        print("\nNo specific criteria found")

if __name__ == "__main__":
    debug_search_criteria()
