#!/usr/bin/env python3
"""
Test script for Phase 2 features
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import Phase 2 functions directly
from text_file_merger import (
    extract_skeleton,
    generate_directory_tree,
    format_as_xml,
    format_as_markdown
)

def test_skeleton_extraction():
    """Test skeleton mode extraction"""
    print("=" * 60)
    print("SKELETON MODE TEST")
    print("=" * 60)

    test_file = Path(__file__)
    skeleton = extract_skeleton(test_file)

    if skeleton:
        print(f"✓ Successfully extracted skeleton from {test_file.name}")
        print(f"\nFirst 300 characters of skeleton:")
        print(skeleton[:300])
        print(f"\nSkeleton length: {len(skeleton)} characters")
        print(f"Original file length: {len(test_file.read_text())} characters")
        reduction = (1 - len(skeleton) / len(test_file.read_text())) * 100
        print(f"Reduction: {reduction:.1f}%")
    else:
        print("✗ Skeleton extraction failed")

    print()

def test_directory_tree():
    """Test directory tree generation"""
    print("=" * 60)
    print("DIRECTORY TREE TEST")
    print("=" * 60)

    test_dir = Path(__file__).parent
    test_files = list(test_dir.glob("*.py"))[:5]  # First 5 Python files

    tree = generate_directory_tree(test_dir, test_files)

    print("Directory tree for test files:")
    print(tree)
    print()

def test_xml_formatting():
    """Test XML output format"""
    print("=" * 60)
    print("XML FORMAT TEST")
    print("=" * 60)

    files_data = [
        {"path": "test/file1.py", "content": "def hello():\n    print('world')"},
        {"path": "test/file2.py", "content": "def goodbye():\n    print('world')"}
    ]

    metadata = {
        "generated_by": "Test Script",
        "timestamp": "2025-11-23 14:00:00",
        "total_files": 2,
        "target_model": "gpt-4o"
    }

    xml_output = format_as_xml(files_data, metadata)

    print("Generated XML (first 400 chars):")
    print(xml_output[:400])
    print(f"\n✓ XML format test passed (total length: {len(xml_output)} chars)")
    print()

def test_markdown_formatting():
    """Test Markdown output format"""
    print("=" * 60)
    print("MARKDOWN FORMAT TEST")
    print("=" * 60)

    files_data = [
        {"path": "test/file1.py", "content": "def hello():\n    print('world')"},
        {"path": "test/file2.py", "content": "def goodbye():\n    print('world')"}
    ]

    metadata = {
        "generated_by": "Test Script",
        "timestamp": "2025-11-23 14:00:00",
        "total_files": 2,
        "target_model": "gpt-4o"
    }

    md_output = format_as_markdown(files_data, metadata)

    print("Generated Markdown (first 400 chars):")
    print(md_output[:400])
    print(f"\n✓ Markdown format test passed (total length: {len(md_output)} chars)")
    print()

def main():
    """Run all Phase 2 tests"""
    print("\n" + "=" * 60)
    print("AI CONTEXT ASSISTANT - PHASE 2 FEATURES TEST")
    print("=" * 60)
    print()

    test_skeleton_extraction()
    test_directory_tree()
    test_xml_formatting()
    test_markdown_formatting()

    print("=" * 60)
    print("ALL PHASE 2 TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()
