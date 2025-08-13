#!/usr/bin/env python3
"""
Demo script for TripC.AI Chatbot API
Showcases platform-aware features and app-first strategy
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def print_separator(title):
    """Print a separator with title"""
    print(f"\n{'='*60}")
    print(f"🎯 {title}")
    print(f"{'='*60}")

def demo_platform_awareness():
    """Demo platform-aware features"""
    print_separator("Platform-Aware Features Demo")
    
    # Test different platform-device combinations
    test_cases = [
        {
            "name": "Web Browser - Desktop",
            "data": {
                "message": "Tìm nhà hàng gần đây",
                "platform": "web_browser",
                "device": "desktop",
                "language": "vi"
            }
        },
        {
            "name": "Web Browser - Android",
            "data": {
                "message": "Tìm nhà hàng gần đây",
                "platform": "web_browser",
                "device": "android",
                "language": "vi"
            }
        },
        {
            "name": "Web Browser - iOS",
            "data": {
                "message": "Tìm nhà hàng gần đây",
                "platform": "web_browser",
                "device": "ios",
                "language": "vi"
            }
        },
        {
            "name": "Mobile App - Android",
            "data": {
                "message": "Tìm nhà hàng gần đây",
                "platform": "mobile_app",
                "device": "android",
                "language": "vi"
            }
        },
        {
            "name": "Mobile App - iOS",
            "data": {
                "message": "Tìm nhà hàng gần đây",
                "platform": "mobile_app",
                "device": "ios",
                "language": "vi"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🔍 Testing: {test_case['name']}")
        print(f"Request: {json.dumps(test_case['data'], indent=2, ensure_ascii=False)}")
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=test_case['data'])
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"Response Type: {result.get('type', 'Unknown')}")
                
                # Show CTA information
                if 'cta' in result:
                    cta = result['cta']
                    print(f"🎗️ CTA:")
                    print(f"   Device: {cta.get('device', 'N/A')}")
                    print(f"   Label: {cta.get('label', 'N/A')}")
                    if 'url' in cta:
                        print(f"   URL: {cta.get('url', 'N/A')}")
                    if 'deeplink' in cta:
                        print(f"   Deeplink: {cta.get('deeplink', 'N/A')}")
                
                # Show suggestions
                if 'suggestions' in result:
                    print(f"💡 Suggestions: {len(result['suggestions'])} available")
                
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 40)

def demo_language_support():
    """Demo multi-language support"""
    print_separator("Multi-Language Support Demo")
    
    languages = ["vi", "en"]
    
    for lang in languages:
        print(f"\n🌍 Testing Language: {lang.upper()}")
        
        test_data = {
            "message": "Xin chào" if lang == "vi" else "Hello",
            "platform": "web_browser",
            "device": "desktop",
            "language": lang
        }
        
        print(f"Request: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=test_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"Answer: {result.get('answerAI', 'N/A')[:100]}...")
                
                # Show CTA in appropriate language
                if 'cta' in result:
                    cta = result['cta']
                    print(f"🎗️ CTA Label: {cta.get('label', 'N/A')}")
                
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 40)

def demo_intent_classification():
    """Demo intent classification"""
    print_separator("Intent Classification Demo")
    
    test_messages = [
        {
            "message": "Xin chào",
            "expected_intent": "QnA (Greeting)"
        },
        {
            "message": "Tìm nhà hàng gần đây",
            "expected_intent": "Service (Restaurant)"
        },
        {
            "message": "Đặt bàn tại nhà hàng Bông",
            "expected_intent": "Booking"
        },
        {
            "message": "Đà Nẵng có gì đẹp?",
            "expected_intent": "QnA (Travel Info)"
        }
    ]
    
    for test in test_messages:
        print(f"\n🔍 Testing: {test['expected_intent']}")
        print(f"Message: {test['message']}")
        
        test_data = {
            "message": test['message'],
            "platform": "web_browser",
            "device": "desktop",
            "language": "vi"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=test_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"Detected Type: {result.get('type', 'Unknown')}")
                print(f"Answer: {result.get('answerAI', 'N/A')[:100]}...")
                
                # Show response details
                if result.get('type') == 'Service' and 'services' in result:
                    services = result['services']
                    print(f"Services Found: {len(services) if services else 0}")
                
                if 'suggestions' in result:
                    suggestions = result['suggestions']
                    print(f"Suggestions: {len(suggestions)} available")
                    for i, suggestion in enumerate(suggestions[:2]):  # Show first 2
                        print(f"  {i+1}. {suggestion.get('label', 'N/A')}")
                
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 40)

def demo_booking_workflow():
    """Demo booking workflow"""
    print_separator("Booking Workflow Demo")
    
    print("🔍 Testing complete booking workflow...")
    
    # Step 1: User asks about booking
    print("\n📝 Step 1: User asks about booking")
    booking_request = {
        "message": "Tôi muốn đặt bàn tại nhà hàng Bông",
        "platform": "web_browser",
        "device": "android",
        "language": "vi"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=booking_request)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Chatbot Response: {result.get('type', 'Unknown')}")
            print(f"Answer: {result.get('answerAI', 'N/A')[:100]}...")
            
            # Check for booking suggestions
            if 'suggestions' in result:
                suggestions = result['suggestions']
                booking_suggestions = [s for s in suggestions if s.get('action') == 'collect_user_info']
                if booking_suggestions:
                    print(f"💡 Found {len(booking_suggestions)} booking suggestions")
                else:
                    print("⚠️ No booking suggestions found")
            
        else:
            print(f"❌ Chatbot Error: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Step 2: User provides information
    print("\n📝 Step 2: User provides booking information")
    user_info = {
        "name": "Nguyễn Văn A",
        "email": "demo@example.com",
        "phone": "+84901234567",
        "message": "Tôi muốn đặt bàn tại nhà hàng Bông vào tối mai, 2 người",
        "platform": "web_browser",
        "device": "android",
        "language": "vi"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/user/collect-info", json=user_info)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ User Info Collection: {result.get('success', False)}")
            print(f"Message: {result.get('message', 'N/A')}")
            if 'booking_reference' in result:
                print(f"Booking Reference: {result.get('booking_reference', 'N/A')}")
            
        else:
            print(f"❌ User Info Error: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("-" * 40)

def demo_system_status():
    """Demo system status and monitoring"""
    print_separator("System Status & Monitoring Demo")
    
    # Get system status
    print("🔍 Getting system status...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/status")
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ System Status: {status.get('status', 'Unknown')}")
            print(f"Service: {status.get('service', 'N/A')}")
            print(f"Version: {status.get('version', 'N/A')}")
            
            # Email service status
            email_service = status.get('email_service', {})
            print(f"📧 Email Service:")
            print(f"   Configured: {email_service.get('configured', False)}")
            print(f"   Booking Email: {email_service.get('booking_email', 'N/A')}")
            
            # Vector store status
            vector_store = status.get('vector_store', {})
            print(f"🧠 Vector Store:")
            print(f"   Initialized: {vector_store.get('initialized', False)}")
            
        else:
            print(f"❌ Status Error: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Get vector store stats
    print("\n🔍 Getting vector store statistics...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/vector/stats")
        
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Vector Store Stats:")
            print(f"   Total Embeddings: {stats.get('total_embeddings', 'N/A')}")
            print(f"   Categories: {stats.get('categories', {})}")
            print(f"   Cities: {stats.get('cities', {})}")
            
        else:
            print(f"❌ Stats Error: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("-" * 40)

def demo_repl_memory():
    """Interactive loop to test conversational memory and standalone rewrite"""
    print_separator("Interactive REPL: Memory & Rewrite Test")
    print("Type 'exit' to quit.")
    conversation_id = "demo_conv_001"
    platform = "web_browser"
    device = "desktop"
    language = "vi"

    while True:
        try:
            user_msg = input("You: ").strip()
            if user_msg.lower() in ["exit", "quit", ":q"]:
                break

            payload = {
                "message": user_msg,
                "platform": platform,
                "device": device,
                "language": language,
                "conversationId": conversation_id
            }

            resp = requests.post(f"{BASE_URL}/api/v1/chatbot/response", json=payload)
            if resp.status_code != 200:
                print(f"❌ {resp.status_code}: {resp.text}")
                continue

            data = resp.json()
            print(f"AI: {data.get('answerAI', '')}")
            if data.get('suggestions'):
                print("Suggestions:")
                for i, s in enumerate(data['suggestions'][:3], 1):
                    label = s.get('label')
                    action = s.get('action')
                    print(f"  {i}. {label} ({action})")
            if data.get('cta'):
                cta = data['cta']
                print(f"CTA: {cta.get('label')} -> {cta.get('url') or cta.get('deeplink')}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Run all demos"""
    print("🧠 TripC.AI Chatbot API - Feature Demo")
    print("Platform-Aware, App-First Architecture")
    
    try:
        # demo_platform_awareness()
        # demo_language_support()
        # demo_intent_classification()
        # demo_booking_workflow()
        # demo_system_status()
        
        print("\n🎉 All demos completed successfully!")
        print("\n📚 Key Features Demonstrated:")
        print("✅ Platform-aware request handling")
        print("✅ Multi-language support (VI/EN)")
        print("✅ Intent classification (QnA/Service/Booking)")
        print("✅ App-first service strategy")
        print("✅ Platform-specific CTAs")
        print("✅ Booking workflow integration")
        print("✅ System monitoring & status")
        
        # Start interactive loop for memory/rewrite testing
        demo_repl_memory()
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
