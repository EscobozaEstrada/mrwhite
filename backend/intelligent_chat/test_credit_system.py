#!/usr/bin/env python3
"""
Test script for Intelligent Chat Credit System
"""
import sys
import os

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.credit_service import IntelligentChatCreditService

def test_credit_calculation():
    """Test credit cost calculation"""
    credit_service = IntelligentChatCreditService()
    
    print("🧪 Testing Credit Cost Calculation:")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        ("normal", False, "Normal chat without documents"),
        ("normal", True, "Normal chat with documents"),
        ("health", False, "Health mode without documents"),
        ("health", True, "Health mode with documents"),
        ("wayofdog", False, "Way of Dog mode without documents"),
        ("wayofdog", True, "Way of Dog mode with documents"),
    ]
    
    for mode, has_docs, description in test_cases:
        cost = credit_service._calculate_credit_cost(mode, has_docs)
        print(f"📊 {description}: {cost} credits")
    
    print("\n✅ Credit calculation test completed!")

def main():
    """Run all tests"""
    print("🚀 Starting Intelligent Chat Credit System Tests")
    print("=" * 60)
    
    # Test credit calculation (no database needed)
    test_credit_calculation()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    main()
