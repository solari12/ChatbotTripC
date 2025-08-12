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

async def final_suggestion_test():
    """Final test to confirm suggestion system is completely accurate"""
    
    print("🎯 FINAL SUGGESTION SYSTEM VALIDATION")
    print("=" * 60)
    
    qna_agent = QnAAgent()
    
    # Test key scenarios
    test_scenarios = [
        {
            "name": "Web Browser - Restaurant Query (Vietnamese)",
            "query": "Nhà hàng nào ngon ở Đà Nẵng?",
            "platform": PlatformType.WEB_BROWSER,
            "device": DeviceType.DESKTOP,
            "language": LanguageType.VIETNAMESE,
            "expected_actions": ["show_services", "download_app"],
            "description": "Web users should see restaurant suggestions + app download"
        },
        {
            "name": "Mobile App - Restaurant Query (Vietnamese)",
            "query": "Nhà hàng nào ngon ở Đà Nẵng?",
            "platform": PlatformType.MOBILE_APP,
            "device": DeviceType.ANDROID,
            "language": LanguageType.VIETNAMESE,
            "expected_actions": ["show_services", "collect_user_info"],
            "description": "Mobile users should see restaurant suggestions + booking"
        },
        {
            "name": "Web Browser - Attraction Query (English)",
            "query": "Best tourist spots in Da Nang?",
            "platform": PlatformType.WEB_BROWSER,
            "device": DeviceType.IOS,
            "language": LanguageType.ENGLISH,
            "expected_actions": ["show_attractions", "download_app"],
            "description": "Web users should see attraction suggestions + app download"
        },
        {
            "name": "Mobile App - Culture Query (Vietnamese)",
            "query": "Văn hóa ẩm thực Việt Nam có gì đặc biệt?",
            "platform": PlatformType.MOBILE_APP,
            "device": DeviceType.ANDROID,
            "language": LanguageType.VIETNAMESE,
            "expected_actions": ["show_culture", "collect_user_info"],
            "description": "Mobile users should see culture suggestions + booking"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📋 Test {i}: {scenario['name']}")
        print(f"Query: {scenario['query']}")
        print(f"Platform: {scenario['platform'].value}, Device: {scenario['device'].value}")
        print(f"Expected: {scenario['expected_actions']}")
        print(f"Description: {scenario['description']}")
        print("-" * 50)
        
        try:
            platform_context = PlatformContext(
                platform=scenario['platform'],
                device=scenario['device'],
                language=scenario['language']
            )
            
            response = await qna_agent.search_embedding(scenario['query'], platform_context)
            
            print(f"🤖 Answer: {response.answerAI[:80]}...")
            print(f"\n💡 Suggestions:")
            
            actual_actions = []
            for j, suggestion in enumerate(response.suggestions, 1):
                actual_actions.append(suggestion.action)
                print(f"  {j}. {suggestion.label}")
                print(f"     Detail: {suggestion.detail}")
                print(f"     Action: {suggestion.action}")
            
            # Analyze results
            expected = scenario['expected_actions']
            missing = [action for action in expected if action not in actual_actions]
            extra = [action for action in actual_actions if action not in expected]
            
            print(f"\n📊 Analysis:")
            print(f"Expected actions: {expected}")
            print(f"Actual actions: {actual_actions}")
            
            if not missing and not extra:
                print("✅ PERFECT: All expected actions present, no unexpected actions")
                result = "PERFECT"
            elif not missing:
                print(f"✅ GOOD: All expected actions present, extra: {extra}")
                result = "GOOD"
            elif not extra:
                print(f"⚠️  PARTIAL: Missing {missing}")
                result = "PARTIAL"
            else:
                print(f"❌ ISSUES: Missing {missing}, Extra {extra}")
                result = "FAIL"
            
            # Check semantic relevance
            query_lower = scenario['query'].lower()
            relevant_suggestions = 0
            
            for suggestion in response.suggestions:
                suggestion_text = f"{suggestion.label} {suggestion.detail}".lower()
                if any(keyword in suggestion_text for keyword in ['nhà hàng', 'restaurant', 'địa điểm', 'attraction', 'văn hóa', 'culture']):
                    relevant_suggestions += 1
            
            relevance_score = relevant_suggestions / len(response.suggestions)
            print(f"Semantic relevance: {relevance_score:.1%} ({relevant_suggestions}/{len(response.suggestions)} suggestions relevant)")
            
            results.append({
                "scenario": scenario['name'],
                "result": result,
                "relevance": relevance_score,
                "expected": expected,
                "actual": actual_actions,
                "missing": missing,
                "extra": extra
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append({
                "scenario": scenario['name'],
                "result": "ERROR",
                "error": str(e)
            })
    
    # Final summary
    print(f"\n{'='*60}")
    print("🎯 FINAL SUGGESTION SYSTEM ASSESSMENT")
    print(f"{'='*60}")
    
    perfect_count = sum(1 for r in results if r['result'] == "PERFECT")
    good_count = sum(1 for r in results if r['result'] == "GOOD")
    partial_count = sum(1 for r in results if r['result'] == "PARTIAL")
    fail_count = sum(1 for r in results if r['result'] == "FAIL")
    error_count = sum(1 for r in results if r['result'] == "ERROR")
    
    print(f"Total Tests: {len(results)}")
    print(f"✅ PERFECT: {perfect_count}")
    print(f"✅ GOOD: {good_count}")
    print(f"⚠️  PARTIAL: {partial_count}")
    print(f"❌ FAIL: {fail_count}")
    print(f"💥 ERROR: {error_count}")
    
    # Calculate average relevance
    valid_results = [r for r in results if 'relevance' in r]
    if valid_results:
        avg_relevance = sum(r['relevance'] for r in valid_results) / len(valid_results)
        print(f"\n📈 Average Semantic Relevance: {avg_relevance:.1%}")
    
    # Final verdict
    success_rate = (perfect_count + good_count + partial_count) / len(results)
    
    if success_rate >= 0.8:
        print(f"\n🎉 FINAL VERDICT: SUGGESTION SYSTEM IS ACCURATE AND READY!")
        print(f"Success Rate: {success_rate:.1%}")
        
        if avg_relevance >= 0.5:
            print("✅ Semantic relevance is excellent")
        else:
            print("⚠️  Semantic relevance needs improvement")
            
    else:
        print(f"\n⚠️  FINAL VERDICT: SUGGESTION SYSTEM NEEDS IMPROVEMENT")
        print(f"Success Rate: {success_rate:.1%}")
    
    # Detailed breakdown
    print(f"\n📋 Detailed Results:")
    for result in results:
        icon = "✅" if result['result'] in ["PERFECT", "GOOD"] else "⚠️" if result['result'] == "PARTIAL" else "❌"
        print(f"{icon} {result['scenario']}: {result['result']}")

if __name__ == "__main__":
    print("Starting final suggestion system validation...")
    asyncio.run(final_suggestion_test())
    print("\n🎯 Validation completed!")
