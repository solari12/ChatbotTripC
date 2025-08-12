import asyncio
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from app.agents.qna_agent import QnAAgent
    from app.models.platform_models import PlatformContext, LanguageType, PlatformType, DeviceType
    print("Imports successful")
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)

async def test_architecture_suggestions():
    """Test suggestion system according to platform-aware architecture"""
    
    print("Testing suggestion system against architecture requirements...")
    qna_agent = QnAAgent()
    
    # Test cases based on architecture requirements
    test_cases = [
        {
            "name": "Web Browser - Vietnamese - Restaurant Query",
            "query": "Nhà hàng nào ngon ở Đà Nẵng?",
            "platform": PlatformType.WEB_BROWSER,
            "device": DeviceType.DESKTOP,
            "language": LanguageType.VIETNAMESE,
            "expected_actions": ["show_services", "download_app"],
            "expected_behavior": "Should include download_app action for web users"
        },
        {
            "name": "Mobile App - Vietnamese - Restaurant Query", 
            "query": "Nhà hàng nào ngon ở Đà Nẵng?",
            "platform": PlatformType.MOBILE_APP,
            "device": DeviceType.ANDROID,
            "language": LanguageType.VIETNAMESE,
            "expected_actions": ["show_services", "collect_user_info"],
            "expected_behavior": "Should include collect_user_info for mobile users"
        },
        {
            "name": "Web Browser - English - Attraction Query",
            "query": "Best tourist spots in Da Nang?",
            "platform": PlatformType.WEB_BROWSER,
            "device": DeviceType.IOS,
            "language": LanguageType.ENGLISH,
            "expected_actions": ["show_attractions", "download_app"],
            "expected_behavior": "Should include download_app action for web users"
        },
        {
            "name": "Mobile App - English - Attraction Query",
            "query": "Best tourist spots in Da Nang?",
            "platform": PlatformType.MOBILE_APP,
            "device": DeviceType.IOS,
            "language": LanguageType.ENGLISH,
            "expected_actions": ["show_attractions", "collect_user_info"],
            "expected_behavior": "Should include collect_user_info for mobile users"
        },
        {
            "name": "Web Browser - Vietnamese - Culture Query",
            "query": "Văn hóa ẩm thực Việt Nam có gì đặc biệt?",
            "platform": PlatformType.WEB_BROWSER,
            "device": DeviceType.ANDROID,
            "language": LanguageType.VIETNAMESE,
            "expected_actions": ["show_culture", "download_app"],
            "expected_behavior": "Should include show_culture and download_app for web users"
        },
        {
            "name": "Mobile App - Vietnamese - Culture Query",
            "query": "Văn hóa ẩm thực Việt Nam có gì đặc biệt?",
            "platform": PlatformType.MOBILE_APP,
            "device": DeviceType.ANDROID,
            "language": LanguageType.VIETNAMESE,
            "expected_actions": ["show_culture", "collect_user_info"],
            "expected_behavior": "Should include show_culture and collect_user_info for mobile users"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test Case {i}: {test_case['name']}")
        print(f"Query: {test_case['query']}")
        print(f"Platform: {test_case['platform'].value}, Device: {test_case['device'].value}, Language: {test_case['language'].value}")
        print(f"Expected Behavior: {test_case['expected_behavior']}")
        print(f"{'='*80}")
        
        try:
            platform_context = PlatformContext(
                platform=test_case['platform'],
                device=test_case['device'],
                language=test_case['language']
            )
            
            response = await qna_agent.search_embedding(test_case['query'], platform_context)
            
            print(f"Answer: {response.answerAI[:100]}...")
            print(f"\nGenerated Suggestions:")
            
            # Analyze suggestions
            actual_actions = []
            suggestion_analysis = []
            
            for j, suggestion in enumerate(response.suggestions, 1):
                actual_actions.append(suggestion.action)
                suggestion_analysis.append({
                    "label": suggestion.label,
                    "detail": suggestion.detail,
                    "action": suggestion.action
                })
                
                print(f"  {j}. {suggestion.label}")
                print(f"     Detail: {suggestion.detail}")
                print(f"     Action: {suggestion.action}")
            
            # Check architecture compliance
            expected_actions = test_case['expected_actions']
            missing_actions = [action for action in expected_actions if action not in actual_actions]
            extra_actions = [action for action in actual_actions if action not in expected_actions]
            
            print(f"\nArchitecture Analysis:")
            print(f"- Expected actions: {expected_actions}")
            print(f"- Actual actions: {actual_actions}")
            
            if not missing_actions and not extra_actions:
                print("✅ PERFECT: All expected actions present, no unexpected actions")
                test_result = "PASS"
            elif not missing_actions:
                print(f"✅ GOOD: All expected actions present, extra actions: {extra_actions}")
                test_result = "PASS"
            elif not extra_actions:
                print(f"⚠️  PARTIAL: Missing expected actions: {missing_actions}")
                test_result = "PARTIAL"
            else:
                print(f"❌ ISSUES: Missing {missing_actions}, Extra {extra_actions}")
                test_result = "FAIL"
            
            # Check action validation
            valid_actions = ["show_services", "show_attractions", "collect_user_info", "show_culture", "download_app"]
            invalid_actions = [action for action in actual_actions if action not in valid_actions]
            
            if invalid_actions:
                print(f"❌ INVALID ACTIONS: {invalid_actions} (not in valid list: {valid_actions})")
                test_result = "FAIL"
            else:
                print(f"✅ VALID ACTIONS: All actions are in valid list")
            
            results.append({
                "test_case": test_case['name'],
                "result": test_result,
                "expected_actions": expected_actions,
                "actual_actions": actual_actions,
                "missing_actions": missing_actions,
                "extra_actions": extra_actions,
                "invalid_actions": invalid_actions
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append({
                "test_case": test_case['name'],
                "result": "ERROR",
                "error": str(e)
            })
    
    # Summary
    print(f"\n{'='*80}")
    print("ARCHITECTURE COMPLIANCE SUMMARY")
    print(f"{'='*80}")
    
    pass_count = sum(1 for r in results if r['result'] == "PASS")
    partial_count = sum(1 for r in results if r['result'] == "PARTIAL")
    fail_count = sum(1 for r in results if r['result'] == "FAIL")
    error_count = sum(1 for r in results if r['result'] == "ERROR")
    
    print(f"Total Tests: {len(results)}")
    print(f"✅ PASS: {pass_count}")
    print(f"⚠️  PARTIAL: {partial_count}")
    print(f"❌ FAIL: {fail_count}")
    print(f"💥 ERROR: {error_count}")
    
    if pass_count + partial_count >= len(results) * 0.8:
        print("\n🎉 OVERALL RESULT: Suggestion system is ARCHITECTURE COMPLIANT!")
    else:
        print("\n⚠️  OVERALL RESULT: Suggestion system needs improvements for architecture compliance")
    
    # Detailed results
    print(f"\nDetailed Results:")
    for result in results:
        status_icon = "✅" if result['result'] == "PASS" else "⚠️" if result['result'] == "PARTIAL" else "❌"
        print(f"{status_icon} {result['test_case']}: {result['result']}")

if __name__ == "__main__":
    print("Starting architecture compliance tests...")
    asyncio.run(test_architecture_suggestions())
    print("\nAll tests completed!")
