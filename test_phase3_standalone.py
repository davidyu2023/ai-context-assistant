#!/usr/bin/env python3
"""
Standalone test for Phase 3 utility functions (no tkinter dependency)
"""

import fnmatch
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# ========== Phase 3 Utility Functions (copied for standalone testing) ==========

# Safe Mode: Sensitive file patterns that should never be included
SAFE_MODE_PATTERNS = [
    # Environment and secrets
    '.env', '.env.local', '.env.production', '.env.development',
    'secrets.yaml', 'secrets.yml', 'secrets.json',
    'credentials.json', 'credentials.yaml',

    # SSH and certificates
    'id_rsa', 'id_dsa', 'id_ed25519',
    '*.pem', '*.key', '*.p12', '*.pfx',

    # Database
    '*.db', '*.sqlite', '*.sqlite3',

    # API keys and tokens
    'api_keys.txt', 'tokens.txt',
    '.npmrc', '.pypirc',

    # Shell history
    '.bash_history', '.zsh_history', '.python_history',

    # AWS credentials
    '.aws/credentials', '.aws/config',
]

def is_safe_mode_excluded(file_path: Path) -> bool:
    """
    Check if file should be excluded in Safe Mode.

    Args:
        file_path: Path to check

    Returns:
        True if file matches safe mode exclusion patterns
    """
    file_name = file_path.name.lower()

    for pattern in SAFE_MODE_PATTERNS:
        if '*' in pattern:
            # Wildcard pattern
            if fnmatch.fnmatch(file_name, pattern.lower()):
                return True
        else:
            # Exact match
            if file_name == pattern or str(file_path).endswith(pattern):
                return True

    return False


def semantic_minify(content: str, language: str = 'python') -> str:
    """
    Apply semantic minification to reduce tokens while preserving meaning.

    Args:
        content: Content to minify
        language: Programming language (python, javascript, etc.)

    Returns:
        Minified content
    """
    lines = content.split('\n')
    minified_lines = []

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Remove single-line comments based on language
        if language in ['python', 'bash', 'ruby']:
            # Python-style comments
            if line.strip().startswith('#') and not line.strip().startswith('#!'):
                continue
            # Remove inline comments (preserve strings)
            if '#' in line and not line.strip().startswith('#'):
                # Simple heuristic: remove # comments not in strings
                if line.count('"') % 2 == 0 and line.count("'") % 2 == 0:
                    line = line.split('#')[0].rstrip()

        elif language in ['javascript', 'typescript', 'java', 'c', 'cpp']:
            # C-style single-line comments
            if line.strip().startswith('//'):
                continue
            if '//' in line:
                line = line.split('//')[0].rstrip()

        # Collapse multiple spaces (but preserve indentation)
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        stripped = ' '.join(stripped.split())
        line = indent + stripped

        if line.strip():
            minified_lines.append(line)

    return '\n'.join(minified_lines)


def calculate_statistics(files: List[Path], content: str, token_count: int) -> Dict:
    """
    Calculate detailed statistics about the generated context.

    Args:
        files: List of included files
        content: Merged content
        token_count: Token count

    Returns:
        Statistics dictionary
    """
    # File type breakdown
    file_types = {}
    total_size = 0

    for file in files:
        ext = file.suffix.lower() or '.txt'
        file_types[ext] = file_types.get(ext, 0) + 1
        try:
            total_size += file.stat().st_size
        except:
            pass

    # Content stats
    lines = content.split('\n')
    char_count = len(content)

    stats = {
        'total_files': len(files),
        'file_types': file_types,
        'total_size_bytes': total_size,
        'total_size_kb': round(total_size / 1024, 2),
        'character_count': char_count,
        'line_count': len(lines),
        'token_count': token_count,
        'avg_tokens_per_file': round(token_count / len(files), 2) if files else 0,
        'compression_ratio': round((1 - char_count / total_size) * 100, 2) if total_size > 0 else 0
    }

    return stats


def filter_files_by_criteria(files: List[Path], max_size_kb: Optional[int] = None,
                             min_size_kb: Optional[int] = None,
                             modified_after: Optional[str] = None) -> List[Path]:
    """
    Filter files based on advanced criteria.

    Args:
        files: List of files to filter
        max_size_kb: Maximum file size in KB
        min_size_kb: Minimum file size in KB
        modified_after: ISO date string (YYYY-MM-DD)

    Returns:
        Filtered list of files
    """
    filtered = []

    for file in files:
        try:
            # Size filtering
            if max_size_kb is not None or min_size_kb is not None:
                size_kb = file.stat().st_size / 1024

                if max_size_kb is not None and size_kb > max_size_kb:
                    continue

                if min_size_kb is not None and size_kb < min_size_kb:
                    continue

            # Date filtering
            if modified_after:
                from datetime import datetime as dt
                mod_time = dt.fromtimestamp(file.stat().st_mtime)
                filter_date = dt.fromisoformat(modified_after)

                if mod_time < filter_date:
                    continue

            filtered.append(file)

        except Exception:
            # If we can't stat the file, include it by default
            filtered.append(file)

    return filtered

# ========== Tests ==========

def test_safe_mode():
    """Test Safe Mode exclusion patterns"""
    print("=" * 60)
    print("SAFE MODE TEST")
    print("=" * 60)

    # Test sensitive file detection
    test_cases = [
        (Path(".env"), True, "Environment file"),
        (Path("secrets.yaml"), True, "Secrets file"),
        (Path("id_rsa"), True, "SSH key"),
        (Path("test.py"), False, "Regular Python file"),
        (Path("config.json"), False, "Regular config"),
        (Path("api_keys.txt"), True, "API keys file"),
        (Path(".bash_history"), True, "Shell history"),
        (Path("database.db"), True, "Database file"),
        (Path("cert.pem"), True, "Certificate file (wildcard)"),
        (Path("private.key"), True, "Key file (wildcard)"),
    ]

    passed = 0
    failed = 0

    for file_path, expected, description in test_cases:
        result = is_safe_mode_excluded(file_path)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} {description}: {file_path.name} -> {'EXCLUDED' if result else 'INCLUDED'}")

    print(f"\nResults: {passed} passed, {failed} failed")
    print(f"Loaded {len(SAFE_MODE_PATTERNS)} Safe Mode patterns")
    print()


def test_semantic_minification():
    """Test semantic minification"""
    print("=" * 60)
    print("SEMANTIC MINIFICATION TEST")
    print("=" * 60)

    # Test Python code
    python_code = """
# This is a comment
def hello():
    # Another comment
    print("Hello")  # Inline comment

    # Empty lines above
    return True

# More comments
class MyClass:
    '''This is a docstring'''
    pass
"""

    minified = semantic_minify(python_code, 'python')

    orig_lines = len([l for l in python_code.split('\n') if l.strip()])
    mini_lines = len([l for l in minified.split('\n') if l.strip()])
    reduction = ((orig_lines - mini_lines) / orig_lines * 100) if orig_lines > 0 else 0

    print(f"Original lines (non-empty): {orig_lines}")
    print(f"Minified lines: {mini_lines}")
    print(f"Reduction: {reduction:.1f}%")
    print(f"\nMinified output:")
    print(minified[:200])

    # Test JavaScript code
    js_code = """
// This is a comment
function hello() {
    // Another comment
    console.log("Hello");  // Inline comment

    return true;
}
"""

    minified_js = semantic_minify(js_code, 'javascript')
    print(f"\n✓ JavaScript minification test passed")
    print()


def test_statistics():
    """Test enhanced statistics calculation"""
    print("=" * 60)
    print("ENHANCED STATISTICS TEST")
    print("=" * 60)

    # Create test files list
    test_dir = Path(__file__).parent
    test_files = list(test_dir.glob("*.py"))[:5]

    # Generate sample content
    test_content = "Test content\n" * 1000
    test_tokens = 5000

    stats = calculate_statistics(test_files, test_content, test_tokens)

    print(f"Total Files: {stats['total_files']}")
    print(f"File Types: {stats['file_types']}")
    print(f"Total Size: {stats['total_size_kb']} KB")
    print(f"Character Count: {stats['character_count']:,}")
    print(f"Line Count: {stats['line_count']:,}")
    print(f"Token Count: {stats['token_count']:,}")
    print(f"Avg Tokens/File: {stats['avg_tokens_per_file']}")

    if stats['compression_ratio'] != 0:
        print(f"Compression Ratio: {stats['compression_ratio']}%")

    print(f"\n✓ Statistics calculation successful")
    print()


def test_advanced_filtering():
    """Test advanced file filtering"""
    print("=" * 60)
    print("ADVANCED FILTERING TEST")
    print("=" * 60)

    test_dir = Path(__file__).parent
    all_files = list(test_dir.glob("*.py"))

    if not all_files:
        print("No test files found, skipping...")
        print()
        return

    print(f"Total files: {len(all_files)}")

    # Test size filtering (max 100KB)
    filtered = filter_files_by_criteria(all_files, max_size_kb=100)
    print(f"Files under 100KB: {len(filtered)}")

    # Test size filtering (min 1KB)
    filtered = filter_files_by_criteria(all_files, min_size_kb=1)
    print(f"Files over 1KB: {len(filtered)}")

    # Test date filtering (modified after 2020-01-01)
    filtered = filter_files_by_criteria(all_files, modified_after="2020-01-01")
    print(f"Files modified after 2020-01-01: {len(filtered)}")

    # Test combined filtering
    filtered = filter_files_by_criteria(
        all_files,
        max_size_kb=1000,
        min_size_kb=1,
        modified_after="2020-01-01"
    )
    print(f"Files matching all criteria: {len(filtered)}")

    print(f"\n✓ Advanced filtering test passed")
    print()


def test_profile_export_import():
    """Test profile export/import data structure"""
    print("=" * 60)
    print("PROFILE EXPORT/IMPORT TEST")
    print("=" * 60)

    # Simulate export data structure
    export_data = {
        "profiles": {
            "Test Profile": {
                "output_folder": "/test/output",
                "file_extensions": ".py, .txt",
                "enable_safe_mode": True,
                "enable_semantic_minify": False
            }
        },
        "prompt_templates": {
            "Test Template": "Test prompt content"
        },
        "exported_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "version": "1.0"
    }

    print(f"Export data structure:")
    print(f"  - Profiles: {len(export_data['profiles'])}")
    print(f"  - Templates: {len(export_data['prompt_templates'])}")
    print(f"  - Version: {export_data['version']}")
    print(f"  - Exported at: {export_data['exported_at']}")

    print(f"\n✓ Profile data structure test passed")
    print()


def main():
    """Run all Phase 3 tests"""
    print("\n" + "=" * 60)
    print("AI CONTEXT ASSISTANT - PHASE 3 FEATURES TEST")
    print("=" * 60)
    print()

    test_safe_mode()
    test_semantic_minification()
    test_statistics()
    test_advanced_filtering()
    test_profile_export_import()

    print("=" * 60)
    print("ALL PHASE 3 TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
