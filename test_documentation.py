import os
import re
import json
from typing import Dict, List, Any
from pathlib import Path

def test_api_documentation():
    """Test API documentation consistency and completeness"""
    
    print("📚 TESTING API DOCUMENTATION")
    print("=" * 60)
    
    # Test files
    test_files = [
        "tripc_ai_chatbot_api.md",
        "tripc_ai_chatbot_architecture.md", 
        "api_documentation.md"
    ]
    
    results = []
    
    for file_name in test_files:
        if not os.path.exists(file_name):
            print(f"❌ File not found: {file_name}")
            continue
            
        print(f"\n📋 Testing: {file_name}")
        print("-" * 40)
        
        with open(file_name, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Test cases
        test_cases = [
            {
                "name": "File Structure",
                "test": lambda c: len(c) > 1000,
                "description": "File should have substantial content"
            },
            {
                "name": "API Endpoints",
                "test": lambda c: "POST /api/v1/chatbot/response" in c,
                "description": "Should contain main chatbot endpoint"
            },
            {
                "name": "Platform Context",
                "test": lambda c: "platform" in c and "device" in c and "language" in c,
                "description": "Should mention platform-aware features"
            },
            {
                "name": "Service Types",
                "test": lambda c: "restaurant" in c and "tour" in c and "hotel" in c,
                "description": "Should mention all service types"
            },
            {
                "name": "App-First Strategy",
                "test": lambda c: "app-first" in c.lower() or "download_app" in c,
                "description": "Should mention app-first strategy"
            },
            {
                "name": "Authentication",
                "test": lambda c: "TRIPC_API_TOKEN" in c or "authentication" in c.lower(),
                "description": "Should mention authentication requirements"
            },
            {
                "name": "Response Format",
                "test": lambda c: "ServiceResponse" in c or "QnAResponse" in c,
                "description": "Should document response formats"
            },
            {
                "name": "Error Handling",
                "test": lambda c: "error" in c.lower() and "status" in c.lower(),
                "description": "Should mention error handling"
            }
        ]
        
        file_results = []
        for test_case in test_cases:
            try:
                passed = test_case["test"](content)
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"  {status} {test_case['name']}: {test_case['description']}")
                file_results.append({
                    "test": test_case["name"],
                    "passed": passed,
                    "description": test_case["description"]
                })
            except Exception as e:
                print(f"  💥 ERROR {test_case['name']}: {str(e)}")
                file_results.append({
                    "test": test_case["name"],
                    "passed": False,
                    "error": str(e)
                })
        
        # Calculate score
        passed_tests = sum(1 for r in file_results if r["passed"])
        total_tests = len(file_results)
        score = passed_tests / total_tests if total_tests > 0 else 0
        
        print(f"\n📊 {file_name}: {passed_tests}/{total_tests} tests passed ({score:.1%})")
        
        results.append({
            "file": file_name,
            "score": score,
            "passed": passed_tests,
            "total": total_tests,
            "details": file_results
        })
    
    # Summary
    print(f"\n{'='*60}")
    print("📚 DOCUMENTATION TEST SUMMARY")
    print(f"{'='*60}")
    
    for result in results:
        icon = "✅" if result["score"] >= 0.8 else "⚠️" if result["score"] >= 0.6 else "❌"
        print(f"{icon} {result['file']}: {result['passed']}/{result['total']} ({result['score']:.1%})")
    
    overall_score = sum(r["score"] for r in results) / len(results) if results else 0
    print(f"\n🎯 Overall Documentation Score: {overall_score:.1%}")
    
    if overall_score >= 0.8:
        print("🎉 EXCELLENT: Documentation is comprehensive and accurate!")
    elif overall_score >= 0.6:
        print("✅ GOOD: Documentation is mostly complete")
    else:
        print("⚠️  NEEDS IMPROVEMENT: Documentation needs work")
    
    return results

def test_api_specification_consistency():
    """Test consistency between API specification and implementation"""
    
    print(f"\n🔍 TESTING API SPECIFICATION CONSISTENCY")
    print("=" * 60)
    
    # Read API documentation
    api_doc_path = "tripc_ai_chatbot_api.md"
    if not os.path.exists(api_doc_path):
        print(f"❌ API documentation not found: {api_doc_path}")
        return
    
    with open(api_doc_path, 'r', encoding='utf-8') as f:
        api_content = f.read()
    
    # Extract API specifications
    specifications = {
        "endpoints": [],
        "request_fields": [],
        "response_fields": [],
        "service_types": []
    }
    
    # Extract endpoints
    endpoint_pattern = r'```\s*\n(?:GET|POST|PUT|DELETE)\s+([^\s]+)'
    endpoints = re.findall(endpoint_pattern, api_content)
    specifications["endpoints"] = endpoints
    
    # Extract request fields
    request_pattern = r'"([^"]+)":\s*"[^"]*",?\s*//\s*([^"]+)'
    request_fields = re.findall(request_pattern, api_content)
    specifications["request_fields"] = request_fields
    
    # Extract service types
    service_pattern = r'"type":\s*"([^"]+)"'
    service_types = re.findall(service_pattern, api_content)
    specifications["service_types"] = list(set(service_types))
    
    print(f"📋 Extracted Specifications:")
    print(f"  Endpoints: {len(specifications['endpoints'])}")
    print(f"  Request Fields: {len(specifications['request_fields'])}")
    print(f"  Service Types: {specifications['service_types']}")
    
    # Test consistency with implementation
    consistency_tests = [
        {
            "name": "Main Chatbot Endpoint",
            "expected": "/api/v1/chatbot/response",
            "found": any("/api/v1/chatbot/response" in ep for ep in specifications["endpoints"])
        },
        {
            "name": "User Info Endpoint", 
            "expected": "/api/v1/user/collect-info",
            "found": any("/api/v1/user/collect-info" in ep for ep in specifications["endpoints"])
        },
        {
            "name": "Platform Context Fields",
            "expected": ["platform", "device", "language"],
            "found": all(field in str(specifications["request_fields"]) for field in ["platform", "device", "language"])
        },
        {
            "name": "Service Response Types",
            "expected": ["Service", "QnA"],
            "found": all(stype in specifications["service_types"] for stype in ["Service", "QnA"])
        }
    ]
    
    print(f"\n🔍 Consistency Tests:")
    passed = 0
    for test in consistency_tests:
        status = "✅ PASS" if test["found"] else "❌ FAIL"
        print(f"  {status} {test['name']}: Expected {test['expected']}")
        if test["found"]:
            passed += 1
    
    consistency_score = passed / len(consistency_tests)
    print(f"\n📊 API Consistency Score: {consistency_score:.1%} ({passed}/{len(consistency_tests)})")
    
    return consistency_score

def test_architecture_documentation():
    """Test architecture documentation completeness"""
    
    print(f"\n🏗️ TESTING ARCHITECTURE DOCUMENTATION")
    print("=" * 60)
    
    arch_doc_path = "tripc_ai_chatbot_architecture.md"
    if not os.path.exists(arch_doc_path):
        print(f"❌ Architecture documentation not found: {arch_doc_path}")
        return
    
    with open(arch_doc_path, 'r', encoding='utf-8') as f:
        arch_content = f.read()
    
    # Architecture components to check
    components = [
        "Platform-Aware Architecture",
        "App-First Strategy", 
        "AI Agent Orchestrator",
        "QnA Agent",
        "Service Agent",
        "CTA System Engine",
        "TripC API Integration",
        "Vector Store",
        "Email Service",
        "LangGraph Workflow"
    ]
    
    print(f"🏗️ Architecture Components:")
    found_components = []
    for component in components:
        found = component.lower() in arch_content.lower()
        status = "✅" if found else "❌"
        print(f"  {status} {component}")
        if found:
            found_components.append(component)
    
    completeness_score = len(found_components) / len(components)
    print(f"\n📊 Architecture Completeness: {completeness_score:.1%} ({len(found_components)}/{len(components)})")
    
    return completeness_score

def test_implementation_files():
    """Test actual implementation files exist and match documentation"""
    
    print(f"\n🔧 TESTING IMPLEMENTATION FILES")
    print("=" * 60)
    
    # Check key implementation files
    implementation_files = [
        "src/app/main.py",
        "src/app/agents/qna_agent.py",
        "src/app/agents/service_agent.py", 
        "src/app/agents/ai_orchestrator.py",
        "src/app/vector/pgvector_store.py",
        "src/app/services/tripc_api.py",
        "src/app/services/email_service.py",
        "src/app/core/cta_engine.py",
        "src/app/core/platform_context.py",
        "src/app/models/schemas.py"
    ]
    
    print(f"🔧 Implementation Files:")
    found_files = []
    for file_path in implementation_files:
        exists = os.path.exists(file_path)
        status = "✅" if exists else "❌"
        print(f"  {status} {file_path}")
        if exists:
            found_files.append(file_path)
    
    # Check specific implementations
    specific_tests = []
    
    # Test Vector Store implementation
    if os.path.exists("src/app/vector/pgvector_store.py"):
        with open("src/app/vector/pgvector_store.py", 'r', encoding='utf-8') as f:
            vector_content = f.read()
            has_pgvector_class = "class PgVectorStore" in vector_content
            has_search_method = "def search" in vector_content
            has_embedding_method = "def get_embedding" in vector_content
            
            specific_tests.extend([
                ("PgVectorStore Class", has_pgvector_class),
                ("Search Method", has_search_method), 
                ("Embedding Method", has_embedding_method)
            ])
    
    # Test LangGraph workflow
    if os.path.exists("src/app/core/langgraph_workflow.py"):
        with open("src/app/core/langgraph_workflow.py", 'r', encoding='utf-8') as f:
            langgraph_content = f.read()
            has_langgraph_import = "langgraph" in langgraph_content.lower()
            has_workflow = "workflow" in langgraph_content.lower()
            
            specific_tests.extend([
                ("LangGraph Import", has_langgraph_import),
                ("Workflow Implementation", has_workflow)
            ])
    
    # Test TripC API integration
    if os.path.exists("src/app/services/tripc_api.py"):
        with open("src/app/services/tripc_api.py", 'r', encoding='utf-8') as f:
            tripc_content = f.read()
            has_tripc_client = "class TripCAPIClient" in tripc_content
            has_restaurant_method = "def get_restaurants" in tripc_content
            has_auth = "authorization" in tripc_content.lower()
            
            specific_tests.extend([
                ("TripC API Client", has_tripc_client),
                ("Restaurant Methods", has_restaurant_method),
                ("Authentication", has_auth)
            ])
    
    print(f"\n🔧 Implementation Details:")
    passed_impl = 0
    for test_name, passed in specific_tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}")
        if passed:
            passed_impl += 1
    
    implementation_score = len(found_files) / len(implementation_files)
    detail_score = passed_impl / len(specific_tests) if specific_tests else 0
    
    print(f"\n📊 Implementation Files: {len(found_files)}/{len(implementation_files)} ({implementation_score:.1%})")
    print(f"📊 Implementation Details: {passed_impl}/{len(specific_tests)} ({detail_score:.1%})")
    
    return (implementation_score + detail_score) / 2

def test_implementation_summary():
    """Test implementation summary accuracy"""
    
    print(f"\n📋 TESTING IMPLEMENTATION SUMMARY")
    print("=" * 60)
    
    impl_doc_path = "IMPLEMENTATION_SUMMARY.md"
    if not os.path.exists(impl_doc_path):
        print(f"❌ Implementation summary not found: {impl_doc_path}")
        return
    
    with open(impl_doc_path, 'r', encoding='utf-8') as f:
        impl_content = f.read()
    
    # Check implementation status
    status_patterns = [
        (r"100% Complete", "Complete implementations"),
        (r"✅", "Completed features"),
        (r"🔄", "In progress features"),
        (r"❌", "Missing features")
    ]
    
    print(f"📋 Implementation Status:")
    total_items = 0
    completed_items = 0
    
    for pattern, description in status_patterns:
        matches = re.findall(pattern, impl_content)
        count = len(matches)
        total_items += count
        if "Complete" in description or "✅" in description:
            completed_items += count
        print(f"  {description}: {count}")
    
    if total_items > 0:
        completion_rate = completed_items / total_items
        print(f"\n📊 Implementation Completion Rate: {completion_rate:.1%}")
    else:
        print(f"\n📊 No implementation status found")
        completion_rate = 0
    
    return completion_rate

def main():
    """Run all documentation tests"""
    
    print("🧪 COMPREHENSIVE DOCUMENTATION TESTING")
    print("=" * 80)
    
    # Run all tests
    doc_results = test_api_documentation()
    api_consistency = test_api_specification_consistency()
    arch_completeness = test_architecture_documentation()
    impl_files = test_implementation_files()
    impl_completion = test_implementation_summary()
    
    # Final summary
    print(f"\n{'='*80}")
    print("🎯 FINAL DOCUMENTATION ASSESSMENT")
    print(f"{'='*80}")
    
    scores = {
        "API Documentation": doc_results[0]["score"] if doc_results else 0,
        "API Consistency": api_consistency,
        "Architecture Completeness": arch_completeness,
        "Implementation Files": impl_files,
        "Implementation Summary": impl_completion
    }
    
    for name, score in scores.items():
        icon = "✅" if score >= 0.8 else "⚠️" if score >= 0.6 else "❌"
        print(f"{icon} {name}: {score:.1%}")
    
    overall_score = sum(scores.values()) / len(scores)
    print(f"\n🎯 Overall Documentation Quality: {overall_score:.1%}")
    
    if overall_score >= 0.8:
        print("🎉 EXCELLENT: Documentation is comprehensive and well-maintained!")
    elif overall_score >= 0.6:
        print("✅ GOOD: Documentation is mostly complete and accurate")
    else:
        print("⚠️  NEEDS IMPROVEMENT: Documentation requires attention")
    
    print(f"\n📚 Documentation is ready for review and deployment!")

if __name__ == "__main__":
    main()
