#!/usr/bin/env python3
"""
Simple test script for Phase 1 utility functions (no GUI dependencies)
"""

import re
from pathlib import Path
from typing import List, Tuple

# Test dependencies
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

try:
    import pathspec
    PATHSPEC_AVAILABLE = True
except ImportError:
    PATHSPEC_AVAILABLE = False

# Binary detection function
def is_binary_file(file_path: Path) -> bool:
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\x00' in chunk
    except Exception:
        return True

# PII sanitization function
def sanitize_pii(content: str, custom_names: List[str] = None) -> Tuple[str, List[str]]:
    redactions = []
    sanitized = content

    if custom_names is None:
        custom_names = []

    default_names = ['davidyu', 'david yu']
    all_names = list(set(default_names + custom_names))

    for i, name in enumerate(all_names, 1):
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        if pattern.search(sanitized):
            sanitized = pattern.sub(f'<USER_{i}>', sanitized)
            redactions.append(f"Replaced '{name}' with <USER_{i}>")

    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, sanitized)
    if emails:
        sanitized = re.sub(email_pattern, '<EMAIL_ADDRESS>', sanitized)
        redactions.append(f"Redacted {len(set(emails))} email address(es)")

    api_patterns = [
        (r'\bsk-[A-Za-z0-9]{48}\b', 'OpenAI API key'),
        (r'\bAKIA[0-9A-Z]{16}\b', 'AWS Access Key'),
    ]

    for pattern, key_type in api_patterns:
        if re.search(pattern, sanitized):
            sanitized = re.sub(pattern, '<REDACTED_API_KEY>', sanitized)
            redactions.append(f"Redacted {key_type}")

    return sanitized, redactions

# Token counting function
def count_tokens(text: str) -> int:
    if not TIKTOKEN_AVAILABLE:
        return len(text) // 4
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 4

# Cost estimation function
def estimate_cost(token_count: int, model: str = "gpt-4o") -> Tuple[float, str]:
    pricing = {
        "gpt-4o": 2.50,
        "gpt-4o-mini": 0.15,
        "claude-3.5-sonnet": 3.00,
    }
    cost_per_million = pricing.get(model, 2.50)
    cost = (token_count / 1_000_000) * cost_per_million
    return cost, model

# Run tests
def main():
    print("=" * 60)
    print("PHASE 1 FEATURES TEST")
    print("=" * 60)
    print()

    # Test 1: Dependencies
    print("Dependencies:")
    print(f"  tiktoken: {TIKTOKEN_AVAILABLE}")
    print(f"  pyperclip: {PYPERCLIP_AVAILABLE}")
    print(f"  pathspec: {PATHSPEC_AVAILABLE}")
    print()

    # Test 2: Binary detection
    print("Binary Detection:")
    test_file = Path(__file__)
    is_bin = is_binary_file(test_file)
    print(f"  {test_file.name} is binary: {is_bin} (expected: False)")
    print(f"  Result: {'PASS' if not is_bin else 'FAIL'}")
    print()

    # Test 3: PII sanitization
    print("PII Sanitization:")
    test_content = """
    Author: davidyu
    Email: test@example.com
    Contact: David Yu at davidyu@company.com
    API: sk-1234567890abcdefghijklmnopqrstuvwxyz123456789012
    """
    sanitized, redactions = sanitize_pii(test_content)
    print(f"  Redactions: {len(redactions)}")
    for r in redactions:
        print(f"    - {r}")

    has_davidyu = "davidyu" in sanitized.lower()
    has_email = "@example.com" in sanitized
    has_api = "sk-1234567890" in sanitized

    print(f"  'davidyu' removed: {'PASS' if not has_davidyu else 'FAIL'}")
    print(f"  Email removed: {'PASS' if not has_email else 'FAIL'}")
    print(f"  API key removed: {'PASS' if not has_api else 'FAIL'}")
    print()

    # Test 4: Token counting
    print("Token Counting:")
    test_text = "Hello, world! This is a test."
    tokens = count_tokens(test_text)
    print(f"  Text: '{test_text}'")
    print(f"  Tokens: {tokens}")
    print(f"  Method: {'tiktoken' if TIKTOKEN_AVAILABLE else 'approximation'}")
    print()

    # Test 5: Cost estimation
    print("Cost Estimation:")
    test_tokens = 10000
    for model in ["gpt-4o", "gpt-4o-mini", "claude-3.5-sonnet"]:
        cost, _ = estimate_cost(test_tokens, model)
        print(f"  {model}: {test_tokens:,} tokens = ${cost:.6f}")
    print()

    print("=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()
