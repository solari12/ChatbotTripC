#!/usr/bin/env python3
import re

def test_email_regex():
    """Test email regex pattern"""
    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    
    test_emails = [
        "tuan111004@gmail.com",
        "test@example.com", 
        "user.name@domain.co.uk",
        "invalid-email",
        "test@",
        "@domain.com"
    ]
    
    print("🧪 Testing Email Regex Pattern")
    print("=" * 40)
    print(f"Pattern: {pattern}")
    print()
    
    for email in test_emails:
        match = re.search(pattern, email)
        result = "✅ MATCH" if match else "❌ NO MATCH"
        print(f"{email:<25} -> {result}")
        if match:
            print(f"  Extracted: {match.group(0)}")

if __name__ == "__main__":
    test_email_regex()

