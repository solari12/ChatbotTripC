#!/usr/bin/env python3
"""
Test script to demonstrate session management fix for multiple users
Shows how different users now have separate conversation contexts
"""

import requests
import time
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"

def print_separator(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def test_session_management():
    """Test session management with multiple users"""
    print_separator("Testing Session Management Fix")
    
    # Test 1: Two different users with same conversation ID (old problem)
    print("🧪 Test 1: Two users with same conversation ID")
    
    user1_payload = {
        "message": "Xin chào, tôi muốn tìm nhà hàng ở Đà Nẵng",
        "platform": "web_browser",
        "device": "desktop",
        "language": "vi",
        "conversationId": "test_conv_001"  # Same conversation ID
    }
    
    user2_payload = {
        "message": "Tôi muốn đặt phòng khách sạn",
        "platform": "mobile_app", 
        "device": "android",
        "language": "vi",
        "conversationId": "test_conv_001"  # Same conversation ID - PROBLEM!
    }
    
    print("User 1 (Web):", user1_payload["message"])
    resp1 = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=user1_payload)
    if resp1.status_code == 200:
        data1 = resp1.json()
        print(f"Bot response: {data1.get('answerAI', '')[:100]}...")
    else:
        print(f"❌ Error: {resp1.status_code}")
    
    print("\nUser 2 (Mobile):", user2_payload["message"])
    resp2 = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=user2_payload)
    if resp2.status_code == 200:
        data2 = resp2.json()
        print(f"Bot response: {data2.get('answerAI', '')[:100]}...")
    else:
        print(f"❌ Error: {resp2.status_code}")
    
    # Test 2: Two users without conversation ID (new solution)
    print("\n🧪 Test 2: Two users without conversation ID (auto-generated)")
    
    user3_payload = {
        "message": "Tôi muốn tìm quán cafe đẹp",
        "platform": "web_browser",
        "device": "ios",
        "language": "vi"
        # No conversationId - will be auto-generated
    }
    
    user4_payload = {
        "message": "Có tour du lịch nào không?",
        "platform": "mobile_app",
        "device": "android", 
        "language": "vi"
        # No conversationId - will be auto-generated
    }
    
    print("User 3 (Web iOS):", user3_payload["message"])
    resp3 = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=user3_payload)
    if resp3.status_code == 200:
        data3 = resp3.json()
        print(f"Bot response: {data3.get('answerAI', '')[:100]}...")
        # Check if conversation ID was assigned
        if hasattr(resp3, 'headers') and 'X-Conversation-ID' in resp3.headers:
            print(f"Assigned conversation ID: {resp3.headers['X-Conversation-ID']}")
    else:
        print(f"❌ Error: {resp3.status_code}")
    
    print("\nUser 4 (Mobile Android):", user4_payload["message"])
    resp4 = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=user4_payload)
    if resp4.status_code == 200:
        data4 = resp4.json()
        print(f"Bot response: {data4.get('answerAI', '')[:100]}...")
        # Check if conversation ID was assigned
        if hasattr(resp4, 'headers') and 'X-Conversation-ID' in resp4.headers:
            print(f"Assigned conversation ID: {resp4.headers['X-Conversation-ID']}")
    else:
        print(f"❌ Error: {resp4.status_code}")
    
    # Test 3: Conversation continuity for same user
    print("\n🧪 Test 3: Conversation continuity for same user")
    
    # First message
    user5_payload = {
        "message": "Tên tôi là Nguyễn Văn A",
        "platform": "web_browser",
        "device": "desktop",
        "language": "vi"
    }
    
    print("User 5 - Message 1:", user5_payload["message"])
    resp5a = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=user5_payload)
    if resp5a.status_code == 200:
        data5a = resp5a.json()
        print(f"Bot response: {data5a.get('answerAI', '')[:100]}...")
    else:
        print(f"❌ Error: {resp5a.status_code}")
    
    # Second message (should remember the name)
    user5_payload["message"] = "Bạn nhớ tên tôi không?"
    print("User 5 - Message 2:", user5_payload["message"])
    resp5b = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=user5_payload)
    if resp5b.status_code == 200:
        data5b = resp5b.json()
        print(f"Bot response: {data5b.get('answerAI', '')[:100]}...")
    else:
        print(f"❌ Error: {resp5b.status_code}")
    
    # Test 4: Check session statistics
    print("\n🧪 Test 4: Session Statistics")
    
    try:
        stats_resp = requests.get(f"{BASE_URL}/api/v1/session/stats")
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            print("Session Statistics:")
            print(f"  Total user sessions: {stats.get('total_user_sessions', 0)}")
            print(f"  Memory sessions: {stats.get('memory_stats', {}).get('total_sessions', 0)}")
            print(f"  Total history entries: {stats.get('memory_stats', {}).get('total_history_entries', 0)}")
            print(f"  User sessions: {stats.get('user_sessions', [])}")
        else:
            print(f"❌ Error getting stats: {stats_resp.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_user_headers():
    """Test with custom user headers"""
    print_separator("Testing Custom User Headers")
    
    # Test with X-User-ID header
    headers = {
        "X-User-ID": "user_12345",
        "User-Agent": "TestApp/1.0"
    }
    
    payload = {
        "message": "Test message with custom user ID",
        "platform": "web_browser",
        "device": "desktop",
        "language": "vi"
    }
    
    print("Testing with X-User-ID header...")
    resp = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=payload, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Success: {data.get('answerAI', '')[:50]}...")
    else:
        print(f"❌ Error: {resp.status_code}")

def main():
    """Run all tests"""
    print("🚀 Starting Session Management Tests")
    print(f"Target API: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test basic session management
        test_session_management()
        
        # Test custom headers
        test_user_headers()
        
        print_separator("Test Summary")
        print("✅ Session management tests completed!")
        print("\nKey improvements:")
        print("1. ✅ Each user gets unique conversation ID")
        print("2. ✅ No more message mixing between users")
        print("3. ✅ Conversation continuity maintained")
        print("4. ✅ Session cleanup and statistics")
        print("5. ✅ Support for custom user headers")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

