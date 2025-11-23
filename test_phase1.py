#!/usr/bin/env python3
"""
Test script for Phase 1 features
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from text_file_merger import (
    is_binary_file,
    sanitize_pii,
    count_tokens,
    estimate_cost,
    TIKTOKEN_AVAILABLE,
    PYPERCLIP_AVAILABLE,
    PATHSPEC_AVAILABLE
)

def test_dependencies():
    """Test that Phase 1 dependencies are available"""
    print("=" * 60)
    print("DEPENDENCY CHECK")
    print("=" * 60)
    print(f"tiktoken available: {TIKTOKEN_AVAILABLE}")
    print(f"pyperclip available: {PYPERCLIP_AVAILABLE}")
    print(f"pathspec available: {PATHSPEC_AVAILABLE}")
    print()

def test_binary_detection():
    """Test binary file detection"""
    print("=" * 60)
    print("BINARY FILE DETECTION TEST")
    print("=" * 60)

    # Test with Python file (should be text)
    test_file = Path(__file__)
    is_binary = is_binary_file(test_file)
    print(f"File: {test_file.name}")
    print(f"Is binary: {is_binary}")
    print(f"Expected: False")
    print(f"Result: {'PASS' if not is_binary else 'FAIL'}")
    print()

def test_pii_sanitization():
    """Test PII sanitization"""
    print("=" * 60)
    print("PII SANITIZATION TEST")
    print("=" * 60)

    test_content = """
    Author: davidyu
    Email: davidyu@example.com
    Password: secret123456
    API Key: sk-1234567890abcdefghijklmnopqrstuvwxyz123456789012
    Another author: David Yu
    """

    sanitized, redactions = sanitize_pii(test_content, ["davidyu", "david yu"])

    print("Original content (first 100 chars):")
    print(test_content[:100])
    print("\nSanitized content (first 200 chars):")
    print(sanitized[:200])
    print(f"\nRedactions made: {len(redactions)}")
    for r in redactions:
        print(f"  - {r}")

    # Check if sensitive data was removed
    checks = [
        ("davidyu" not in sanitized.lower(), "davidyu removed"),
        ("@example.com" not in sanitized, "email removed"),
        ("secret123456" not in sanitized, "password removed"),
        ("sk-1234567890" not in sanitized, "API key removed"),
    ]

    print("\nValidation:")
    for check, desc in checks:
        print(f"  {desc}: {'PASS' if check else 'FAIL'}")

    print()

def test_token_counting():
    """Test token counting"""
    print("=" * 60)
    print("TOKEN COUNTING TEST")
    print("=" * 60)

    test_text = "Hello, world! This is a test of token counting."
    token_count = count_tokens(test_text)

    print(f"Text: {test_text}")
    print(f"Token count: {token_count}")

    if TIKTOKEN_AVAILABLE:
        print("Using tiktoken for accurate counting")
    else:
        print("Using character approximation (tiktoken not available)")

    print()

def test_cost_estimation():
    """Test cost estimation"""
    print("=" * 60)
    print("COST ESTIMATION TEST")
    print("=" * 60)

    test_tokens = 10000
    models = ["gpt-4o", "gpt-4o-mini", "claude-3.5-sonnet"]

    for model in models:
        cost, model_name = estimate_cost(test_tokens, model)
        print(f"Model: {model_name}")
        print(f"Tokens: {test_tokens:,}")
        print(f"Estimated cost: ${cost:.6f}")
        print()

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AI CONTEXT ASSISTANT - PHASE 1 FEATURES TEST")
    print("=" * 60)
    print()

    test_dependencies()
    test_binary_detection()
    test_pii_sanitization()
    test_token_counting()
    test_cost_estimation()

    print("=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()
