#!/usr/bin/env python3
"""
Test script for TripC.AI Chatbot API
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.text}")
    print()

def test_root():
    """Test root endpoint"""
    print("🔍 Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.text}")
    print()

def test_chatbot_response():
    """Test chatbot response endpoint"""
    print("🔍 Testing chatbot response endpoint...")
    
    # Test valid request
    valid_data = {
        "message": "Xin chào",
        "platform": "web_browser",
        "device": "desktop",
        "language": "vi"
    }
    
    print("Testing valid request...")
    response = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=valid_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"Error: {response.text}")
    print()
    
    # Test invalid platform-device combination
    invalid_data = {
        "message": "Xin chào",
        "platform": "mobile_app",
        "device": "desktop",  # Invalid: mobile_app + desktop
        "language": "vi"
    }
    
    print("Testing invalid platform-device combination...")
    response = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=invalid_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print(f"Expected error: {response.json()}")
    else:
        print(f"Unexpected response: {response.text}")
    print()
    
    # Test missing fields
    missing_data = {
        "message": "Xin chào"
        # Missing platform, device, language
    }
    
    print("Testing missing required fields...")
    response = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=missing_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 422:
        print(f"Expected validation error: {response.json()}")
    else:
        print(f"Unexpected response: {response.text}")
    print()

def test_user_collect_info():
    """Test user info collection endpoint"""
    print("🔍 Testing user info collection endpoint...")
    
    valid_data = {
        "name": "Nguyễn Văn A",
        "email": "user@example.com",
        "phone": "+84901234567",
        "message": "Tôi muốn đặt bàn tại nhà hàng Bông",
        "platform": "web_browser",
        "device": "android",
        "language": "vi"
    }
    
    print("Testing valid user info collection...")
    response = requests.post(f"{BASE_URL}/api/v1/user/collect-info", json=valid_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"Error: {response.text}")
    print()

def test_status():
    """Test status endpoint"""
    print("🔍 Testing status endpoint...")
    response = requests.get(f"{BASE_URL}/api/v1/status")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"Error: {response.text}")
    print()

def test_vector_stats():
    """Test vector stats endpoint"""
    print("🔍 Testing vector stats endpoint...")
    response = requests.get(f"{BASE_URL}/api/v1/vector/stats")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"Error: {response.text}")
    print()

def main():
    """Run all tests"""
    print("🧠 TripC.AI Chatbot API Test Suite")
    print("=" * 50)
    
    try:
        test_health()
        test_root()
        test_chatbot_response()
        test_user_collect_info()
        test_status()
        test_vector_stats()
        
        print("✅ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
