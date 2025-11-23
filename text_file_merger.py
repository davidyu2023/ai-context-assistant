"""
Text File Merger - GUI Application
Combines multiple text files from selected folders into single output files
with clear delimiters and timestamps.

Phase 1 Features:
- Token counting and cost estimation
- Binary file detection
- .gptignore/.gptignore support
- PII sanitization
- Copy to clipboard

Phase 2 Features:
- Project Profiles/Workspaces
- Skeleton Mode (code structure extraction)
- Directory tree visualization
- System Prompt Templates
- Model-specific output formats (XML/Markdown)

Phase 3 Features:
- Safe Mode (sensitive file protection)
- Enhanced statistics and analytics
- Profile import/export
- Advanced filtering (size, date, patterns)
- Semantic minification
- Batch profile processing
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
import re
import ast
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Phase 1 dependencies
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("Warning: tiktoken not available. Token counting disabled.")

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    print("Warning: pyperclip not available. Clipboard features disabled.")

try:
    import pathspec
    PATHSPEC_AVAILABLE = True
except ImportError:
    PATHSPEC_AVAILABLE = False
    print("Warning: pathspec not available. .gitignore support disabled.")


# ============================================================================
# Phase 1 Utility Functions
# ============================================================================

def is_binary_file(file_path: Path) -> bool:
    """
    Detect if a file is binary by checking for NULL bytes.

    Args:
        file_path: Path to the file to check

    Returns:
        True if file appears to be binary, False otherwise
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)  # Read first 1KB
            return b'\x00' in chunk
    except Exception:
        return True  # If we can't read it, treat as binary


def sanitize_pii(content: str, custom_names: List[str] = None) -> Tuple[str, List[str]]:
    """
    Sanitize PII from content including emails, usernames, and passwords.

    Args:
        content: The text content to sanitize
        custom_names: List of custom names/usernames to replace (e.g., ['davidyu', 'david yu'])

    Returns:
        Tuple of (sanitized_content, list of redactions made)
    """
    redactions = []
    sanitized = content

    # Default names to sanitize
    if custom_names is None:
        custom_names = []

    # Add default patterns
    default_names = ['davidyu', 'david yu']
    all_names = list(set(default_names + custom_names))

    # Replace custom names (case-insensitive)
    for i, name in enumerate(all_names, 1):
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        if pattern.search(sanitized):
            sanitized = pattern.sub(f'<USER_{i}>', sanitized)
            redactions.append(f"Replaced '{name}' with <USER_{i}>")

    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, sanitized)
    if emails:
        sanitized = re.sub(email_pattern, '<EMAIL_ADDRESS>', sanitized)
        redactions.append(f"Redacted {len(set(emails))} email address(es)")

    # API Keys (common patterns)
    api_patterns = [
        (r'\bsk-[A-Za-z0-9]{48}\b', 'OpenAI API key'),
        (r'\bAKIA[0-9A-Z]{16}\b', 'AWS Access Key'),
        (r'\bxoxb-[0-9]+-[0-9]+-[A-Za-z0-9]+\b', 'Slack Bot Token'),
        (r'\bghp_[A-Za-z0-9]{36}\b', 'GitHub Personal Access Token'),
    ]

    for pattern, key_type in api_patterns:
        if re.search(pattern, sanitized):
            sanitized = re.sub(pattern, '<REDACTED_API_KEY>', sanitized)
            redactions.append(f"Redacted {key_type}")

    # Generic high-entropy strings that look like passwords/secrets (basic heuristic)
    # Look for strings like password=xxx, pwd=xxx, secret=xxx
    password_patterns = [
        r'(password|pwd|passwd|pass)\s*[=:]\s*["\']?([A-Za-z0-9!@#$%^&*()_+\-=\[\]{};:,.<>?]{8,})["\']?',
        r'(secret|token|key)\s*[=:]\s*["\']?([A-Za-z0-9!@#$%^&*()_+\-=\[\]{};:,.<>?]{16,})["\']?',
    ]

    for pattern in password_patterns:
        matches = re.findall(pattern, sanitized, re.IGNORECASE)
        if matches:
            sanitized = re.sub(pattern, r'\1=<REDACTED_SECRET>', sanitized, flags=re.IGNORECASE)
            redactions.append(f"Redacted {len(matches)} password/secret assignment(s)")

    return sanitized, redactions


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text using tiktoken.

    Args:
        text: The text to count tokens for
        model: The model to use for tokenization (gpt-4, gpt-3.5-turbo, etc.)

    Returns:
        Number of tokens, or character count / 4 if tiktoken unavailable
    """
    if not TIKTOKEN_AVAILABLE:
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4

    try:
        # Use cl100k_base encoding (used by GPT-4, GPT-3.5-turbo)
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception as e:
        print(f"Token counting error: {e}")
        return len(text) // 4


def estimate_cost(token_count: int, model: str = "gpt-4o") -> Tuple[float, str]:
    """
    Estimate API cost based on token count.

    Args:
        token_count: Number of input tokens
        model: Model name for pricing

    Returns:
        Tuple of (cost in USD, model name)
    """
    # Pricing per 1M tokens (as of 2024)
    pricing = {
        "gpt-4o": 2.50,
        "gpt-4o-mini": 0.15,
        "claude-3.5-sonnet": 3.00,
        "claude-3-opus": 15.00,
    }

    cost_per_million = pricing.get(model, 2.50)
    cost = (token_count / 1_000_000) * cost_per_million

    return cost, model


# ============================================================================
# Phase 2 Utility Functions
# ============================================================================

def extract_skeleton(file_path: Path) -> Optional[str]:
    """
    Extract code skeleton (class/function signatures only) from Python files.

    Args:
        file_path: Path to the Python file

    Returns:
        Skeleton code string or None if extraction fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        skeleton_lines = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Extract class definition
                class_line = f"class {node.name}"
                if node.bases:
                    bases = ', '.join(ast.unparse(base) for base in node.bases)
                    class_line += f"({bases})"
                class_line += ":"
                skeleton_lines.append(class_line)

                # Extract docstring if present
                if (ast.get_docstring(node)):
                    docstring = ast.get_docstring(node)
                    skeleton_lines.append(f'    """{docstring}"""')

                # Extract methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        # Build function signature
                        args = []
                        for arg in item.args.args:
                            arg_str = arg.arg
                            if arg.annotation:
                                arg_str += f": {ast.unparse(arg.annotation)}"
                            args.append(arg_str)

                        func_sig = f"    def {item.name}({', '.join(args)})"
                        if item.returns:
                            func_sig += f" -> {ast.unparse(item.returns)}"
                        func_sig += ":"
                        skeleton_lines.append(func_sig)

                        # Add docstring if present
                        if ast.get_docstring(item):
                            docstring = ast.get_docstring(item)
                            skeleton_lines.append(f'        """{docstring}"""')

                        skeleton_lines.append("        ...")
                        skeleton_lines.append("")

                skeleton_lines.append("")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.col_offset == 0:
                # Top-level function
                args = []
                for arg in node.args.args:
                    arg_str = arg.arg
                    if arg.annotation:
                        arg_str += f": {ast.unparse(arg.annotation)}"
                    args.append(arg_str)

                func_sig = f"def {node.name}({', '.join(args)})"
                if node.returns:
                    func_sig += f" -> {ast.unparse(node.returns)}"
                func_sig += ":"
                skeleton_lines.append(func_sig)

                if ast.get_docstring(node):
                    docstring = ast.get_docstring(node)
                    skeleton_lines.append(f'    """{docstring}"""')

                skeleton_lines.append("    ...")
                skeleton_lines.append("")

        return '\n'.join(skeleton_lines) if skeleton_lines else None

    except Exception as e:
        # If AST parsing fails, return None (not a valid Python file or syntax error)
        return None


def generate_directory_tree(folder_path: Path, files: List[Path], prefix: str = "") -> str:
    """
    Generate a text-based directory tree visualization.

    Args:
        folder_path: Root folder path
        files: List of files to include in tree
        prefix: Prefix for tree formatting (used in recursion)

    Returns:
        Tree structure as string
    """
    tree_lines = []

    # Build a nested structure
    structure = {}
    for file in files:
        try:
            relative = file.relative_to(folder_path)
            parts = relative.parts

            current = structure
            for i, part in enumerate(parts):
                if i == len(parts) - 1:  # File
                    if 'files' not in current:
                        current['files'] = []
                    current['files'].append(part)
                else:  # Directory
                    if 'dirs' not in current:
                        current['dirs'] = {}
                    if part not in current['dirs']:
                        current['dirs'][part] = {}
                    current = current['dirs'][part]
        except ValueError:
            continue

    # Generate tree representation
    def build_tree(node: Dict, prefix: str = "", is_last: bool = True) -> List[str]:
        lines = []

        # Add directories
        if 'dirs' in node:
            dirs = sorted(node['dirs'].items())
            for i, (dir_name, sub_node) in enumerate(dirs):
                is_last_dir = (i == len(dirs) - 1) and 'files' not in node
                connector = "└── " if is_last_dir else "├── "
                lines.append(f"{prefix}{connector}{dir_name}/")

                extension = "    " if is_last_dir else "│   "
                lines.extend(build_tree(sub_node, prefix + extension, is_last_dir))

        # Add files
        if 'files' in node:
            files = sorted(node['files'])
            for i, file_name in enumerate(files):
                is_last_file = i == len(files) - 1
                connector = "└── " if is_last_file else "├── "
                lines.append(f"{prefix}{connector}{file_name}")

        return lines

    tree_lines.append(f"{folder_path.name}/")
    tree_lines.extend(build_tree(structure))

    return '\n'.join(tree_lines)


def format_as_xml(files_data: List[Dict[str, str]], metadata: Dict) -> str:
    """
    Format merged files as XML (optimized for Claude).

    Args:
        files_data: List of dicts with 'path' and 'content' keys
        metadata: Metadata dictionary

    Returns:
        XML-formatted string
    """
    lines = ["<?xml version='1.0' encoding='UTF-8'?>"]
    lines.append("<context>")

    # Metadata section
    lines.append("  <metadata>")
    for key, value in metadata.items():
        lines.append(f"    <{key}>{value}</{key}>")
    lines.append("  </metadata>")

    # Documents section
    lines.append("  <documents>")
    for i, file_data in enumerate(files_data, 1):
        lines.append(f"    <document index='{i}'>")
        lines.append(f"      <source>{file_data['path']}</source>")
        lines.append(f"      <document_content>")
        # Escape XML special characters
        content = file_data['content'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        lines.append(f"{content}")
        lines.append(f"      </document_content>")
        lines.append(f"    </document>")
    lines.append("  </documents>")

    lines.append("</context>")
    return '\n'.join(lines)


def format_as_markdown(files_data: List[Dict[str, str]], metadata: Dict) -> str:
    """
    Format merged files as Markdown (optimized for GPT).

    Args:
        files_data: List of dicts with 'path' and 'content' keys
        metadata: Metadata dictionary

    Returns:
        Markdown-formatted string
    """
    lines = ["# AI Context"]
    lines.append("")

    # Metadata section
    lines.append("## Metadata")
    for key, value in metadata.items():
        lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
    lines.append("")

    # Files section
    lines.append("## Files")
    lines.append("")

    for file_data in files_data:
        lines.append(f"### File: `{file_data['path']}`")
        lines.append("")

        # Determine language for syntax highlighting
        path = Path(file_data['path'])
        ext_to_lang = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.cs': 'csharp',
            '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.php': 'php',
            '.swift': 'swift', '.kt': 'kotlin', '.scala': 'scala',
            '.sh': 'bash', '.sql': 'sql', '.json': 'json', '.xml': 'xml',
            '.yaml': 'yaml', '.yml': 'yaml', '.md': 'markdown', '.html': 'html',
            '.css': 'css', '.scss': 'scss'
        }
        lang = ext_to_lang.get(path.suffix.lower(), '')

        lines.append(f"```{lang}")
        lines.append(file_data['content'])
        lines.append("```")
        lines.append("")

    return '\n'.join(lines)


# ============================================================================
# Phase 3 Utility Functions
# ============================================================================

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
            import fnmatch
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


class Config:
    """Handles persistent configuration storage"""

    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.data = self.load()

    def load(self) -> dict:
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return self.default_config()
        return self.default_config()

    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    @staticmethod
    def default_config() -> dict:
        """Return default configuration"""
        return {
            "output_folder": "",
            "file_extensions": ".txt, .py, .md, .json, .xml, .csv",
            "source_folders": [],
            # Phase 1 settings
            "enable_pii_sanitization": True,
            "custom_sanitize_names": ["davidyu", "david yu"],
            "enable_binary_detection": True,
            "token_soft_limit": 32000,
            "token_hard_limit": 128000,
            "respect_gitignore": True,
            # Phase 2 settings
            "enable_skeleton_mode": False,
            "output_format": "standard",  # standard, xml, markdown
            "show_directory_tree": True,
            "system_prompt": "",
            "current_profile": "Default",
            "profiles": {},
            "prompt_templates": {
                "Code Review": "You are a senior software engineer. Review this code for:\n- Code quality and best practices\n- Potential bugs\n- Performance issues\n- Security vulnerabilities",
                "Documentation": "You are a technical writer. Generate comprehensive documentation for this codebase including:\n- Overview\n- Architecture\n- API documentation\n- Usage examples",
                "Refactoring": "You are an expert in code refactoring. Analyze this code and suggest improvements for:\n- Code structure\n- Design patterns\n- Maintainability\n- Testability"
            },
            # Phase 3 settings
            "enable_safe_mode": True,
            "enable_semantic_minify": False,
            "show_statistics": True,
            "max_file_size_kb": None,
            "min_file_size_kb": None,
            "modified_after": None
        }

    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.data.get(key, default)

    def set(self, key: str, value):
        """Set configuration value and save"""
        self.data[key] = value
        self.save()

    # Phase 2: Profile Management Methods
    def save_profile(self, profile_name: str, profile_data: Dict):
        """Save a profile configuration"""
        if 'profiles' not in self.data:
            self.data['profiles'] = {}
        self.data['profiles'][profile_name] = profile_data
        self.save()

    def load_profile(self, profile_name: str) -> Optional[Dict]:
        """Load a profile configuration"""
        return self.data.get('profiles', {}).get(profile_name)

    def delete_profile(self, profile_name: str):
        """Delete a profile"""
        if 'profiles' in self.data and profile_name in self.data['profiles']:
            del self.data['profiles'][profile_name]
            self.save()

    def get_profile_names(self) -> List[str]:
        """Get list of all profile names"""
        return list(self.data.get('profiles', {}).keys())

    # Phase 3: Profile Import/Export Methods
    def export_profiles(self, export_path: str) -> bool:
        """Export all profiles to a JSON file"""
        try:
            export_data = {
                "profiles": self.data.get('profiles', {}),
                "prompt_templates": self.data.get('prompt_templates', {}),
                "exported_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "version": "1.0"
            }
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting profiles: {e}")
            return False

    def import_profiles(self, import_path: str, merge: bool = True) -> bool:
        """
        Import profiles from a JSON file.

        Args:
            import_path: Path to import file
            merge: If True, merge with existing profiles; if False, replace all
        """
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)

            if 'profiles' in import_data:
                if merge:
                    # Merge with existing profiles
                    if 'profiles' not in self.data:
                        self.data['profiles'] = {}
                    self.data['profiles'].update(import_data['profiles'])
                else:
                    # Replace all profiles
                    self.data['profiles'] = import_data['profiles']

            if 'prompt_templates' in import_data:
                if merge:
                    if 'prompt_templates' not in self.data:
                        self.data['prompt_templates'] = {}
                    self.data['prompt_templates'].update(import_data['prompt_templates'])
                else:
                    self.data['prompt_templates'] = import_data['prompt_templates']

            self.save()
            return True
        except Exception as e:
            print(f"Error importing profiles: {e}")
            return False


class FolderEntry:
    """Represents a single folder entry with its settings"""

    def __init__(self, parent_frame, index: int, on_remove_callback):
        self.index = index
        self.on_remove = on_remove_callback

        # Create frame for this entry
        self.frame = ttk.LabelFrame(parent_frame, text=f"Source Folder {index + 1}",
                                    padding="10")
        self.frame.pack(fill=tk.X, padx=5, pady=5)

        # Folder path
        path_frame = ttk.Frame(self.frame)
        path_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(path_frame, text="Folder:").pack(side=tk.LEFT)
        self.folder_path = tk.StringVar()
        self.folder_entry = ttk.Entry(path_frame, textvariable=self.folder_path,
                                      width=50, state='readonly')
        self.folder_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        ttk.Button(path_frame, text="Browse...",
                  command=self.browse_folder).pack(side=tk.LEFT)

        # Options frame
        options_frame = ttk.Frame(self.frame)
        options_frame.pack(fill=tk.X, pady=(0, 5))

        # Include subfolders checkbox
        self.include_subfolders = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Exclude subfolders",
                       variable=self.include_subfolders).pack(side=tk.LEFT, padx=(0, 15))

        # Include archive folder checkbox
        self.include_archive = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Include archive folder",
                       variable=self.include_archive).pack(side=tk.LEFT)

        # Output filename
        output_frame = ttk.Frame(self.frame)
        output_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(output_frame, text="Output Name:").pack(side=tk.LEFT)
        self.output_name = tk.StringVar(value=f"merged_output_{index + 1}")
        ttk.Entry(output_frame, textvariable=self.output_name,
                 width=30).pack(side=tk.LEFT, padx=5)
        ttk.Label(output_frame, text="(timestamp will be added)").pack(side=tk.LEFT)

        # Remove button
        ttk.Button(self.frame, text="Remove This Folder",
                  command=self.remove).pack(pady=(5, 0))

    def browse_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.folder_path.set(folder)

    def remove(self):
        """Remove this folder entry"""
        self.frame.destroy()
        self.on_remove(self)

    def get_config(self) -> Optional[Dict]:
        """Get configuration for this folder entry"""
        if not self.folder_path.get():
            return None

        return {
            "folder_path": self.folder_path.get(),
            "exclude_subfolders": self.include_subfolders.get(),
            "include_archive": self.include_archive.get(),
            "output_name": self.output_name.get()
        }

    def set_config(self, config: Dict):
        """Set configuration for this folder entry"""
        self.folder_path.set(config.get("folder_path", ""))
        self.include_subfolders.set(config.get("exclude_subfolders", False))
        self.include_archive.set(config.get("include_archive", False))
        self.output_name.set(config.get("output_name", f"merged_output_{self.index + 1}"))


class TextFileMergerApp:
    """Main application class"""

    MAX_FOLDERS = 5

    def __init__(self, root):
        self.root = root
        self.root.title("AI Context Assistant - Text File Merger")
        self.root.geometry("900x750")

        # Configuration
        self.config = Config()

        # Folder entries
        self.folder_entries: List[FolderEntry] = []

        # Setup GUI
        self.setup_gui()

        # Load saved source folders
        self.load_source_folders()

    def setup_gui(self):
        """Setup the GUI components"""

        # Main container with scrollbar
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Folders Section (Output + Source Folders)
        folders_frame = ttk.LabelFrame(main_container, text="Folders", padding="10")
        folders_frame.pack(fill=tk.X, pady=(0, 10))

        # Output folder
        output_folder_frame = ttk.Frame(folders_frame)
        output_folder_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(output_folder_frame, text="Output Folder:").pack(side=tk.LEFT)
        self.output_folder = tk.StringVar(value=self.config.get("output_folder", ""))
        ttk.Entry(output_folder_frame, textvariable=self.output_folder,
                 width=50, state='readonly').pack(side=tk.LEFT, padx=5, fill=tk.X,
                                                  expand=True)
        ttk.Button(output_folder_frame, text="Browse...",
                  command=self.browse_output_folder).pack(side=tk.LEFT)

        # File extensions
        extensions_frame = ttk.Frame(folders_frame)
        extensions_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(extensions_frame, text="File Extensions:").pack(side=tk.LEFT)
        self.file_extensions = tk.StringVar(
            value=self.config.get("file_extensions", ".txt, .py, .md"))
        ttk.Entry(extensions_frame, textvariable=self.file_extensions,
                 width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(extensions_frame,
                 text="(comma-separated, e.g., .txt, .py, .md)").pack(side=tk.LEFT)

        # Source Folders subsection
        ttk.Label(folders_frame, text="Source Folders:",
                 font=('', 9, 'bold')).pack(anchor=tk.W, pady=(5, 5))

        # Canvas with scrollbar for folder entries
        canvas_frame = ttk.Frame(folders_frame, height=180)
        canvas_frame.pack(fill=tk.X, pady=(0, 5))
        canvas_frame.pack_propagate(False)  # Maintain fixed height

        self.canvas = tk.Canvas(canvas_frame, height=180, bg='white')
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical",
                                 command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add folder button
        button_frame = ttk.Frame(folders_frame)
        button_frame.pack(fill=tk.X, pady=(5, 5))

        self.add_folder_btn = ttk.Button(button_frame, text="Add Source Folder",
                                         command=self.add_folder_entry)
        self.add_folder_btn.pack(side=tk.LEFT)

        self.folder_count_label = ttk.Label(button_frame,
                                           text=f"Folders: 0/{self.MAX_FOLDERS}")
        self.folder_count_label.pack(side=tk.LEFT, padx=10)

        # Save settings button
        ttk.Button(folders_frame, text="Save Settings",
                  command=self.save_settings).pack(pady=(5, 0))

        # Basic Settings Section
        phase1_frame = ttk.LabelFrame(main_container, text="Basic Settings", padding="10")
        phase1_frame.pack(fill=tk.X, pady=(0, 10))

        # Row 1: PII sanitization and binary detection
        row1_frame = ttk.Frame(phase1_frame)
        row1_frame.pack(fill=tk.X, pady=(0, 5))

        self.enable_pii = tk.BooleanVar(value=self.config.get("enable_pii_sanitization", True))
        ttk.Checkbutton(row1_frame, text="Enable PII Sanitization",
                       variable=self.enable_pii).pack(side=tk.LEFT)

        self.enable_binary_detect = tk.BooleanVar(value=self.config.get("enable_binary_detection", True))
        ttk.Checkbutton(row1_frame, text="Skip Binary Files",
                       variable=self.enable_binary_detect).pack(side=tk.LEFT, padx=15)

        # Row 2: Token limits
        row2_frame = ttk.Frame(phase1_frame)
        row2_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(row2_frame, text="Soft Limit:").pack(side=tk.LEFT)
        self.token_soft_limit = tk.StringVar(value=str(self.config.get("token_soft_limit", 32000)))
        ttk.Entry(row2_frame, textvariable=self.token_soft_limit, width=10).pack(side=tk.LEFT, padx=5)

        ttk.Label(row2_frame, text="Hard Limit:").pack(side=tk.LEFT, padx=(10, 0))
        self.token_hard_limit = tk.StringVar(value=str(self.config.get("token_hard_limit", 128000)))
        ttk.Entry(row2_frame, textvariable=self.token_hard_limit, width=10).pack(side=tk.LEFT, padx=5)

        self.respect_gitignore = tk.BooleanVar(value=self.config.get("respect_gitignore", True))
        ttk.Checkbutton(row2_frame, text="Respect .gitignore/.gptignore",
                       variable=self.respect_gitignore).pack(side=tk.LEFT, padx=15)

        # Row 3: Token budget display
        budget_frame = ttk.Frame(phase1_frame)
        budget_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(budget_frame, text="Token Budget:").pack(side=tk.LEFT)

        # Progress bar for token budget
        self.token_progress = ttk.Progressbar(budget_frame, length=300, mode='determinate')
        self.token_progress.pack(side=tk.LEFT, padx=5)

        # Token count and cost label
        self.token_info_label = ttk.Label(budget_frame, text="0 tokens ($0.00)")
        self.token_info_label.pack(side=tk.LEFT, padx=5)

        # Output Options Section
        phase2_frame = ttk.LabelFrame(main_container, text="Output Options", padding="10")
        phase2_frame.pack(fill=tk.X, pady=(0, 10))

        # Row 1: Skeleton mode and output format
        p2_row1_frame = ttk.Frame(phase2_frame)
        p2_row1_frame.pack(fill=tk.X, pady=(0, 5))

        self.enable_skeleton = tk.BooleanVar(value=self.config.get("enable_skeleton_mode", False))
        ttk.Checkbutton(p2_row1_frame, text="Skeleton Mode (signatures only)",
                       variable=self.enable_skeleton).pack(side=tk.LEFT)

        self.show_dir_tree = tk.BooleanVar(value=self.config.get("show_directory_tree", True))
        ttk.Checkbutton(p2_row1_frame, text="Show Directory Tree",
                       variable=self.show_dir_tree).pack(side=tk.LEFT, padx=15)

        ttk.Label(p2_row1_frame, text="Output Format:").pack(side=tk.LEFT, padx=(15, 0))
        self.output_format = tk.StringVar(value=self.config.get("output_format", "standard"))
        format_combo = ttk.Combobox(p2_row1_frame, textvariable=self.output_format,
                                    values=["standard", "xml", "markdown"],
                                    state='readonly', width=12)
        format_combo.pack(side=tk.LEFT, padx=5)

        # Row 2: Profile management
        p2_row2_frame = ttk.Frame(phase2_frame)
        p2_row2_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(p2_row2_frame, text="Profile:").pack(side=tk.LEFT)

        # Profile dropdown
        self.current_profile = tk.StringVar(value=self.config.get("current_profile", "Default"))
        self.profile_combo = ttk.Combobox(p2_row2_frame, textvariable=self.current_profile,
                                         state='readonly', width=20)
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.update_profile_list()

        ttk.Button(p2_row2_frame, text="Load", command=self.load_profile_action,
                  width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(p2_row2_frame, text="Save As...", command=self.save_profile_action,
                  width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(p2_row2_frame, text="Delete", command=self.delete_profile_action,
                  width=8).pack(side=tk.LEFT, padx=2)

        # Row 3: System Prompt
        p2_row3_frame = ttk.Frame(phase2_frame)
        p2_row3_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        prompt_label_frame = ttk.Frame(p2_row3_frame)
        prompt_label_frame.pack(fill=tk.X)

        ttk.Label(prompt_label_frame, text="System Prompt (optional):").pack(side=tk.LEFT)
        ttk.Label(prompt_label_frame, text="Template:").pack(side=tk.LEFT, padx=(15, 0))

        # Template dropdown
        self.prompt_template = tk.StringVar(value="None")
        template_names = ["None"] + list(self.config.get("prompt_templates", {}).keys())
        self.template_combo = ttk.Combobox(prompt_label_frame, textvariable=self.prompt_template,
                                          values=template_names, state='readonly', width=15)
        self.template_combo.pack(side=tk.LEFT, padx=5)
        self.template_combo.bind('<<ComboboxSelected>>', self.load_template)

        # System prompt text area
        self.system_prompt = scrolledtext.ScrolledText(p2_row3_frame, height=3, wrap=tk.WORD)
        self.system_prompt.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.system_prompt.insert('1.0', self.config.get("system_prompt", ""))

        # File Filtering & Security Section
        phase3_frame = ttk.LabelFrame(main_container, text="File Filtering & Security", padding="10")
        phase3_frame.pack(fill=tk.X, pady=(0, 10))

        # Row 1: Security and optimization
        p3_row1_frame = ttk.Frame(phase3_frame)
        p3_row1_frame.pack(fill=tk.X, pady=(0, 5))

        self.enable_safe_mode = tk.BooleanVar(value=self.config.get("enable_safe_mode", True))
        ttk.Checkbutton(p3_row1_frame, text="Safe Mode (exclude sensitive files)",
                       variable=self.enable_safe_mode).pack(side=tk.LEFT)

        self.enable_minify = tk.BooleanVar(value=self.config.get("enable_semantic_minify", False))
        ttk.Checkbutton(p3_row1_frame, text="Semantic Minify (remove comments)",
                       variable=self.enable_minify).pack(side=tk.LEFT, padx=15)

        self.show_stats = tk.BooleanVar(value=self.config.get("show_statistics", True))
        ttk.Checkbutton(p3_row1_frame, text="Show Statistics",
                       variable=self.show_stats).pack(side=tk.LEFT, padx=15)

        # Row 2: Profile import/export
        p3_row2_frame = ttk.Frame(phase3_frame)
        p3_row2_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(p3_row2_frame, text="Profiles:").pack(side=tk.LEFT)
        ttk.Button(p3_row2_frame, text="Import...", command=self.import_profiles_action,
                  width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(p3_row2_frame, text="Export...", command=self.export_profiles_action,
                  width=10).pack(side=tk.LEFT, padx=2)

        # Row 3: Advanced filtering
        p3_row3_frame = ttk.Frame(phase3_frame)
        p3_row3_frame.pack(fill=tk.X, pady=(0, 0))

        ttk.Label(p3_row3_frame, text="File Filters:").pack(side=tk.LEFT)

        ttk.Label(p3_row3_frame, text="Max Size (KB):").pack(side=tk.LEFT, padx=(10, 0))
        self.max_size_entry = ttk.Entry(p3_row3_frame, width=8)
        self.max_size_entry.pack(side=tk.LEFT, padx=5)
        if self.config.get("max_file_size_kb"):
            self.max_size_entry.insert(0, str(self.config.get("max_file_size_kb")))

        ttk.Label(p3_row3_frame, text="Min Size (KB):").pack(side=tk.LEFT, padx=(10, 0))
        self.min_size_entry = ttk.Entry(p3_row3_frame, width=8)
        self.min_size_entry.pack(side=tk.LEFT, padx=5)
        if self.config.get("min_file_size_kb"):
            self.min_size_entry.insert(0, str(self.config.get("min_file_size_kb")))

        ttk.Label(p3_row3_frame, text="Modified After:").pack(side=tk.LEFT, padx=(10, 0))
        self.modified_after_entry = ttk.Entry(p3_row3_frame, width=12)
        self.modified_after_entry.pack(side=tk.LEFT, padx=5)
        if self.config.get("modified_after"):
            self.modified_after_entry.insert(0, str(self.config.get("modified_after")))
        ttk.Label(p3_row3_frame, text="(YYYY-MM-DD)", font=('', 8)).pack(side=tk.LEFT)

        # Action Buttons
        action_frame = ttk.Frame(main_container)
        action_frame.pack(fill=tk.X)

        ttk.Button(action_frame, text="Generate Output Files",
                  command=self.generate_outputs,
                  style='Accent.TButton').pack(side=tk.LEFT, padx=5)

        # Add Copy to Clipboard button (Phase 1)
        if PYPERCLIP_AVAILABLE:
            ttk.Button(action_frame, text="Copy to Clipboard",
                      command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=5)

        ttk.Button(action_frame, text="Clear All Folders",
                  command=self.clear_all_folders).pack(side=tk.LEFT)

        ttk.Button(action_frame, text="Help",
                  command=self.show_help).pack(side=tk.RIGHT, padx=5)

        # Status/Log Section
        log_frame = ttk.LabelFrame(main_container, text="Status Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8,
                                                  state='disabled', wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def browse_output_folder(self):
        """Open dialog to select output folder"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)
            self.config.set("output_folder", folder)
            self.log(f"Output folder set to: {folder}")

    def save_settings(self):
        """Save current settings to config"""
        self.config.set("output_folder", self.output_folder.get())
        self.config.set("file_extensions", self.file_extensions.get())

        # Save Phase 1 settings
        self.config.set("enable_pii_sanitization", self.enable_pii.get())
        self.config.set("enable_binary_detection", self.enable_binary_detect.get())
        self.config.set("respect_gitignore", self.respect_gitignore.get())

        try:
            self.config.set("token_soft_limit", int(self.token_soft_limit.get()))
            self.config.set("token_hard_limit", int(self.token_hard_limit.get()))
        except ValueError:
            self.log("Warning: Invalid token limit values, using defaults")

        # Save Phase 2 settings
        self.config.set("enable_skeleton_mode", self.enable_skeleton.get())
        self.config.set("output_format", self.output_format.get())
        self.config.set("show_directory_tree", self.show_dir_tree.get())
        self.config.set("system_prompt", self.system_prompt.get('1.0', 'end-1c'))

        self.save_source_folders()
        self.log("Settings saved successfully")
        messagebox.showinfo("Settings", "Settings saved successfully!")

    def save_source_folders(self):
        """Save current source folder configurations and all settings to config"""
        folder_configs = []
        for entry in self.folder_entries:
            config = entry.get_config()
            if config:
                folder_configs.append(config)
        self.config.set("source_folders", folder_configs)

        # Save all Phase 1, 2, 3 settings
        self.config.set("output_folder", self.output_folder.get())
        self.config.set("file_extensions", self.file_extensions.get())
        self.config.set("enable_pii_sanitization", self.enable_pii.get())
        self.config.set("enable_binary_detection", self.enable_binary_detect.get())
        self.config.set("respect_gitignore", self.respect_gitignore.get())
        self.config.set("enable_skeleton_mode", self.enable_skeleton.get())
        self.config.set("output_format", self.output_format.get())
        self.config.set("show_directory_tree", self.show_dir_tree.get())
        self.config.set("system_prompt", self.system_prompt.get('1.0', 'end-1c'))

        # Phase 3 settings
        self.config.set("enable_safe_mode", self.enable_safe_mode.get())
        self.config.set("enable_semantic_minify", self.enable_minify.get())
        self.config.set("show_statistics", self.show_stats.get())

        # Advanced filtering
        try:
            max_val = self.max_size_entry.get().strip()
            self.config.set("max_file_size_kb", int(max_val) if max_val else None)
        except ValueError:
            self.config.set("max_file_size_kb", None)

        try:
            min_val = self.min_size_entry.get().strip()
            self.config.set("min_file_size_kb", int(min_val) if min_val else None)
        except ValueError:
            self.config.set("min_file_size_kb", None)

        modified_val = self.modified_after_entry.get().strip()
        self.config.set("modified_after", modified_val if modified_val else None)

    def load_source_folders(self):
        """Load saved source folder configurations from config"""
        saved_folders = self.config.get("source_folders", [])
        for folder_config in saved_folders:
            if len(self.folder_entries) >= self.MAX_FOLDERS:
                break
            entry = FolderEntry(self.scrollable_frame, len(self.folder_entries),
                              self.remove_folder_entry)
            entry.set_config(folder_config)
            self.folder_entries.append(entry)
        self.update_folder_count()
        if saved_folders:
            self.log(f"Loaded {len(saved_folders)} saved source folder(s)")

        # Update canvas to show loaded entries
        if saved_folders:
            self.scrollable_frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def add_folder_entry(self):
        """Add a new folder entry"""
        if len(self.folder_entries) >= self.MAX_FOLDERS:
            messagebox.showwarning("Limit Reached",
                                  f"Maximum of {self.MAX_FOLDERS} folders allowed")
            return

        entry = FolderEntry(self.scrollable_frame, len(self.folder_entries),
                          self.remove_folder_entry)
        self.folder_entries.append(entry)
        self.update_folder_count()
        self.log(f"Added folder entry {len(self.folder_entries)}")

        # Update canvas to show new entry
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def remove_folder_entry(self, entry: FolderEntry):
        """Remove a folder entry"""
        if entry in self.folder_entries:
            self.folder_entries.remove(entry)
            self.update_folder_count()
            # Reindex remaining entries
            for i, e in enumerate(self.folder_entries):
                e.index = i
                e.frame.configure(text=f"Source Folder {i + 1}")
            self.log(f"Removed folder entry")

            # Update canvas after removing entry
            self.scrollable_frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def clear_all_folders(self):
        """Clear all folder entries"""
        if not self.folder_entries:
            return

        if messagebox.askyesno("Clear All",
                              "Are you sure you want to remove all folder entries?"):
            for entry in self.folder_entries[:]:
                entry.frame.destroy()
            self.folder_entries.clear()
            self.update_folder_count()
            self.log("All folder entries cleared")

    def update_folder_count(self):
        """Update folder count label"""
        count = len(self.folder_entries)
        self.folder_count_label.config(text=f"Folders: {count}/{self.MAX_FOLDERS}")
        self.add_folder_btn.config(state='normal' if count < self.MAX_FOLDERS
                                  else 'disabled')

    def log(self, message: str):
        """Add message to log"""
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

    def get_file_extensions(self) -> List[str]:
        """Parse and return list of file extensions"""
        extensions_str = self.file_extensions.get()
        extensions = [ext.strip() for ext in extensions_str.split(',')]
        # Ensure extensions start with a dot
        return [ext if ext.startswith('.') else f'.{ext}' for ext in extensions if ext]

    def load_ignore_patterns(self, folder_path: Path) -> Optional['pathspec.PathSpec']:
        """
        Load .gptignore or .gitignore patterns from folder.

        Args:
            folder_path: The folder to check for ignore files

        Returns:
            PathSpec object or None if no ignore file found
        """
        if not PATHSPEC_AVAILABLE or not self.respect_gitignore.get():
            return None

        # Check for .gptignore first, then .gitignore
        for ignore_file in ['.gptignore', '.gitignore']:
            ignore_path = folder_path / ignore_file
            if ignore_path.exists():
                try:
                    with open(ignore_path, 'r') as f:
                        patterns = f.read().splitlines()
                    self.log(f"  Loaded {len(patterns)} patterns from {ignore_file}")
                    return pathspec.PathSpec.from_lines('gitwildmatch', patterns)
                except Exception as e:
                    self.log(f"  Error loading {ignore_file}: {e}")

        return None

    def _is_in_archive_folder(self, file_path: Path) -> bool:
        """Check if a file is within an archive folder"""
        # Check if any parent directory is named 'archive' or 'archived'
        for parent in file_path.parents:
            if parent.name.lower() in ['archive', 'archived', 'archives']:
                return True
        return False

    def collect_files(self, folder_path: str, exclude_subfolders: bool,
                     extensions: List[str], include_archive: bool = False) -> Tuple[List[Path], List[str]]:
        """
        Collect all files from folder matching extensions with Phase 1 filtering.

        Returns:
            Tuple of (list of valid files, list of skipped file reasons)
        """
        files = []
        skipped = []
        folder = Path(folder_path)

        # Load ignore patterns
        ignore_spec = self.load_ignore_patterns(folder)

        if exclude_subfolders:
            # Only get files in the root folder
            candidate_files = [f for f in folder.iterdir() if f.is_file()]
        else:
            # Recursively get all files
            candidate_files = []
            for ext in extensions:
                candidate_files.extend(folder.rglob(f"*{ext}"))

        # Filter files based on Phase 1 criteria
        for file_path in candidate_files:
            # Check extension
            if file_path.suffix.lower() not in extensions:
                continue

            # Check archive folder
            if not include_archive and self._is_in_archive_folder(file_path):
                skipped.append(f"{file_path.name} (in archive folder)")
                continue

            # Check gitignore patterns
            if ignore_spec:
                try:
                    relative_path = file_path.relative_to(folder)
                    if ignore_spec.match_file(str(relative_path)):
                        skipped.append(f"{file_path.name} (matched .gitignore/.gptignore)")
                        continue
                except ValueError:
                    pass

            # Check if binary
            if self.enable_binary_detect.get() and is_binary_file(file_path):
                skipped.append(f"{file_path.name} (binary file)")
                continue

            # Phase 3: Check Safe Mode
            if self.enable_safe_mode.get() and is_safe_mode_excluded(file_path):
                skipped.append(f"{file_path.name} (excluded by Safe Mode)")
                continue

            files.append(file_path)

        # Phase 3: Apply advanced filtering
        max_size = self.config.get("max_file_size_kb")
        min_size = self.config.get("min_file_size_kb")
        modified_after = self.config.get("modified_after")

        if max_size or min_size or modified_after:
            before_count = len(files)
            files = filter_files_by_criteria(files, max_size, min_size, modified_after)
            filtered_count = before_count - len(files)
            if filtered_count > 0:
                skipped.append(f"{filtered_count} file(s) filtered by size/date criteria")

        return sorted(files), skipped

    def merge_files(self, files: List[Path], output_path: str, source_folder: str) -> Tuple[bool, str, int, List[str]]:
        """
        Merge multiple files with Phase 1, 2 & 3 features:
        - Phase 1: PII sanitization, token counting, binary detection, .gitignore support
        - Phase 2: Skeleton mode, directory tree, system prompts, output formats, profiles
        - Phase 3: Safe mode, semantic minification, enhanced statistics, advanced filtering

        Returns:
            Tuple of (success, merged_content, token_count, pii_redactions)
        """
        try:
            source_path = Path(source_folder)
            top_folder = source_path.name
            all_redactions = []
            skeleton_mode = self.enable_skeleton.get()
            output_format = self.output_format.get()

            # Prepare metadata
            metadata = {
                "generated_by": "AI Context Assistant",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "total_files": len(files),
                "output_format": output_format
            }

            if self.enable_pii.get():
                metadata["pii_sanitization"] = "ENABLED"

            if skeleton_mode:
                metadata["skeleton_mode"] = "ENABLED (signatures only)"

            # Process files
            files_data = []

            for file_path in files:
                try:
                    # Calculate relative path
                    try:
                        relative_path = file_path.relative_to(source_path)
                        display_path = f"{top_folder}/{relative_path}"
                    except ValueError:
                        display_path = f"{top_folder}/{file_path.name}"

                    # Read or extract skeleton
                    if skeleton_mode and file_path.suffix.lower() == '.py':
                        content = extract_skeleton(file_path)
                        if content is None:
                            # Fall back to full content if extraction fails
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                                content = infile.read()
                    else:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                            content = infile.read()

                    # Apply PII sanitization
                    if self.enable_pii.get():
                        custom_names = self.config.get("custom_sanitize_names", ["davidyu", "david yu"])
                        content, redactions = sanitize_pii(content, custom_names)
                        if redactions:
                            all_redactions.extend([f"{display_path}: {r}" for r in redactions])

                    # Phase 3: Apply semantic minification
                    if self.enable_minify.get():
                        # Detect language from file extension
                        ext = file_path.suffix.lower()
                        lang_map = {
                            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                            '.java': 'java', '.cpp': 'cpp', '.c': 'c',
                            '.rb': 'ruby', '.sh': 'bash'
                        }
                        language = lang_map.get(ext, 'python')
                        content = semantic_minify(content, language)

                    files_data.append({"path": display_path, "content": content})

                except Exception as e:
                    self.log(f"Error reading {file_path}: {e}")
                    continue

            # Generate output based on format
            if output_format == "xml":
                merged_content = format_as_xml(files_data, metadata)
            elif output_format == "markdown":
                merged_content = format_as_markdown(files_data, metadata)
            else:
                # Standard format
                merged_content = self._format_standard(files_data, metadata, source_path, files)

            # Prepend system prompt if provided
            system_prompt = self.system_prompt.get('1.0', 'end-1c').strip()
            if system_prompt:
                if output_format == "xml":
                    merged_content = f"<!-- System Instructions -->\n{system_prompt}\n\n{merged_content}"
                elif output_format == "markdown":
                    merged_content = f"## System Instructions\n\n{system_prompt}\n\n{merged_content}"
                else:
                    merged_content = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n{'='*80}\n\n{merged_content}"

            # Count tokens (using gpt-4o as reference model)
            token_count = count_tokens(merged_content, "gpt-4o")

            # Phase 3: Calculate enhanced statistics
            if self.show_stats.get():
                stats = calculate_statistics(files, merged_content, token_count)
                self.log(f"\n=== Enhanced Statistics ===")
                self.log(f"Total Files: {stats['total_files']}")
                self.log(f"File Types: {stats['file_types']}")
                self.log(f"Total Size: {stats['total_size_kb']} KB ({stats['total_size_bytes']} bytes)")
                self.log(f"Characters: {stats['character_count']:,}")
                self.log(f"Lines: {stats['line_count']:,}")
                self.log(f"Tokens: {stats['token_count']:,}")
                self.log(f"Avg Tokens/File: {stats['avg_tokens_per_file']}")
                if stats['compression_ratio'] > 0:
                    self.log(f"Compression Ratio: {stats['compression_ratio']}%")

            # Write to file
            with open(output_path, 'w', encoding='utf-8', errors='ignore') as outfile:
                outfile.write(merged_content)

            return True, merged_content, token_count, all_redactions

        except Exception as e:
            self.log(f"Error writing output file: {e}")
            return False, "", 0, []

    def _format_standard(self, files_data: List[Dict[str, str]], metadata: Dict,
                        source_path: Path, files: List[Path]) -> str:
        """Format output in standard format with Phase 2 enhancements"""
        lines = []

        # Header
        lines.append("Generated by AI Context Assistant")
        lines.append(f"Timestamp: {metadata['timestamp']}")
        lines.append(f"Total files: {metadata['total_files']}")

        if "pii_sanitization" in metadata:
            lines.append(f"PII Sanitization: {metadata['pii_sanitization']}")

        if "skeleton_mode" in metadata:
            lines.append(f"Skeleton Mode: {metadata['skeleton_mode']}")

        lines.append("\n" + "="*80)

        # Directory tree (Phase 2 feature)
        if self.show_dir_tree.get() and files:
            lines.append("\nDIRECTORY STRUCTURE:")
            lines.append("="*80)
            tree = generate_directory_tree(source_path, files)
            lines.append(tree)
            lines.append("="*80)

        lines.append("")

        # Files
        for file_data in files_data:
            lines.append("="*80)
            lines.append(f"BEGIN FILE: {file_data['path']}")
            lines.append("="*80)
            lines.append(file_data['content'])

            if file_data['content'] and not file_data['content'].endswith('\n'):
                lines.append("")

            lines.append("="*80)
            lines.append(f"END FILE: {file_data['path']}")
            lines.append("="*80)
            lines.append("")

        return '\n'.join(lines)

    def generate_outputs(self):
        """Generate output files for all configured folders"""
        # Validate settings
        if not self.output_folder.get():
            messagebox.showerror("Error", "Please select an output folder")
            return

        if not os.path.exists(self.output_folder.get()):
            messagebox.showerror("Error", "Output folder does not exist")
            return

        # Get valid folder configurations
        folder_configs = []
        for entry in self.folder_entries:
            config = entry.get_config()
            if config:
                folder_configs.append(config)

        if not folder_configs:
            messagebox.showwarning("No Folders",
                                  "Please add at least one source folder")
            return

        # Get file extensions
        extensions = self.get_file_extensions()
        if not extensions:
            messagebox.showerror("Error",
                               "Please specify at least one file extension")
            return

        self.log("="*60)
        self.log("Starting file merge process...")
        self.log(f"Output folder: {self.output_folder.get()}")
        self.log(f"File extensions: {', '.join(extensions)}")
        self.log(f"Processing {len(folder_configs)} folder(s)")
        self.log("="*60)

        success_count = 0
        total_tokens = 0
        total_redactions = []

        # Process each folder
        for i, config in enumerate(folder_configs, 1):
            folder_path = config['folder_path']
            exclude_subfolders = config['exclude_subfolders']
            include_archive = config.get('include_archive', False)
            output_name = config['output_name']

            self.log(f"\n[{i}/{len(folder_configs)}] Processing: {folder_path}")
            self.log(f"  Exclude subfolders: {exclude_subfolders}")
            self.log(f"  Include archive folder: {include_archive}")

            # Collect files (Phase 1: with binary detection and gitignore support)
            files, skipped = self.collect_files(folder_path, exclude_subfolders, extensions, include_archive)

            if skipped:
                self.log(f"  Skipped {len(skipped)} file(s):")
                for skip_reason in skipped[:5]:  # Show first 5
                    self.log(f"    - {skip_reason}")
                if len(skipped) > 5:
                    self.log(f"    ... and {len(skipped) - 5} more")

            if not files:
                self.log(f"  Warning: No matching files found")
                continue

            self.log(f"  Found {len(files)} file(s)")

            # Generate output filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{output_name}_{timestamp}.txt"
            output_path = os.path.join(self.output_folder.get(), output_filename)

            # Merge files (Phase 1: with PII sanitization and token counting)
            success, content, token_count, redactions = self.merge_files(files, output_path, folder_path)

            if success:
                # Calculate cost (using gpt-4o as reference)
                cost, model = estimate_cost(token_count, "gpt-4o")

                self.log(f"  Success: Created {output_filename}")
                self.log(f"  Tokens: {token_count:,} | Estimated cost: ${cost:.4f} ({model})")

                if redactions:
                    self.log(f"  PII Redactions: {len(redactions)} item(s)")
                    total_redactions.extend(redactions)

                total_tokens += token_count
                success_count += 1

                # Update token budget display
                self.update_token_budget(total_tokens)
            else:
                self.log(f"  Error: Failed to create output file")

        self.log("="*60)
        self.log(f"Process complete: {success_count}/{len(folder_configs)} successful")
        self.log("="*60)

        # Save source folders for next time
        self.save_source_folders()

        messagebox.showinfo("Complete",
                          f"Generated {success_count} output file(s)\n"
                          f"Location: {self.output_folder.get()}")

    # ========================================================================
    # Phase 2: Profile Management Methods
    # ========================================================================

    def update_profile_list(self):
        """Update the profile dropdown with available profiles"""
        profiles = ["Default"] + self.config.get_profile_names()
        self.profile_combo['values'] = profiles
        if self.current_profile.get() not in profiles:
            self.current_profile.set("Default")

    def get_current_state(self) -> Dict:
        """Get current application state as a dictionary"""
        # Parse filter values
        max_size = None
        min_size = None
        modified_after = None

        try:
            max_val = self.max_size_entry.get().strip()
            if max_val:
                max_size = int(max_val)
        except ValueError:
            pass

        try:
            min_val = self.min_size_entry.get().strip()
            if min_val:
                min_size = int(min_val)
        except ValueError:
            pass

        modified_val = self.modified_after_entry.get().strip()
        if modified_val:
            modified_after = modified_val

        return {
            "output_folder": self.output_folder.get(),
            "file_extensions": self.file_extensions.get(),
            "enable_pii_sanitization": self.enable_pii.get(),
            "enable_binary_detection": self.enable_binary_detect.get(),
            "respect_gitignore": self.respect_gitignore.get(),
            "token_soft_limit": self.token_soft_limit.get(),
            "token_hard_limit": self.token_hard_limit.get(),
            "enable_skeleton_mode": self.enable_skeleton.get(),
            "output_format": self.output_format.get(),
            "show_directory_tree": self.show_dir_tree.get(),
            "system_prompt": self.system_prompt.get('1.0', 'end-1c'),
            # Phase 3 settings
            "enable_safe_mode": self.enable_safe_mode.get(),
            "enable_semantic_minify": self.enable_minify.get(),
            "show_statistics": self.show_stats.get(),
            "max_file_size_kb": max_size,
            "min_file_size_kb": min_size,
            "modified_after": modified_after,
            "source_folders": [e.get_config() for e in self.folder_entries if e.get_config()]
        }

    def apply_state(self, state: Dict):
        """Apply a saved state to the current application"""
        self.output_folder.set(state.get("output_folder", ""))
        self.file_extensions.set(state.get("file_extensions", ".txt, .py, .md"))
        self.enable_pii.set(state.get("enable_pii_sanitization", True))
        self.enable_binary_detect.set(state.get("enable_binary_detection", True))
        self.respect_gitignore.set(state.get("respect_gitignore", True))
        self.token_soft_limit.set(str(state.get("token_soft_limit", 32000)))
        self.token_hard_limit.set(str(state.get("token_hard_limit", 128000)))
        self.enable_skeleton.set(state.get("enable_skeleton_mode", False))
        self.output_format.set(state.get("output_format", "standard"))
        self.show_dir_tree.set(state.get("show_directory_tree", True))

        # Phase 3 settings
        self.enable_safe_mode.set(state.get("enable_safe_mode", True))
        self.enable_minify.set(state.get("enable_semantic_minify", False))
        self.show_stats.set(state.get("show_statistics", True))

        # Advanced filtering
        self.max_size_entry.delete(0, tk.END)
        if state.get("max_file_size_kb"):
            self.max_size_entry.insert(0, str(state.get("max_file_size_kb")))

        self.min_size_entry.delete(0, tk.END)
        if state.get("min_file_size_kb"):
            self.min_size_entry.insert(0, str(state.get("min_file_size_kb")))

        self.modified_after_entry.delete(0, tk.END)
        if state.get("modified_after"):
            self.modified_after_entry.insert(0, str(state.get("modified_after")))

        # System prompt
        self.system_prompt.delete('1.0', tk.END)
        self.system_prompt.insert('1.0', state.get("system_prompt", ""))

        # Clear and reload source folders
        for entry in self.folder_entries[:]:
            entry.frame.destroy()
        self.folder_entries.clear()

        for folder_config in state.get("source_folders", []):
            if len(self.folder_entries) < self.MAX_FOLDERS:
                entry = FolderEntry(self.scrollable_frame, len(self.folder_entries),
                                  self.remove_folder_entry)
                entry.set_config(folder_config)
                self.folder_entries.append(entry)

        self.update_folder_count()

        # Update canvas to show loaded entries
        if state.get("source_folders"):
            self.scrollable_frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def save_profile_action(self):
        """Save current state as a new profile"""
        # Ask for profile name
        dialog = tk.Toplevel(self.root)
        dialog.title("Save Profile")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Profile Name:").pack(pady=(10, 5))

        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(pady=5)
        name_entry.focus()

        def save():
            profile_name = name_var.get().strip()
            if not profile_name:
                messagebox.showwarning("Invalid Name", "Please enter a profile name")
                return

            if profile_name == "Default":
                messagebox.showwarning("Reserved Name", "'Default' is a reserved name")
                return

            state = self.get_current_state()
            self.config.save_profile(profile_name, state)
            self.update_profile_list()
            self.current_profile.set(profile_name)
            self.log(f"Saved profile: {profile_name}")
            dialog.destroy()
            messagebox.showinfo("Success", f"Profile '{profile_name}' saved successfully!")

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)

    def load_profile_action(self):
        """Load a saved profile"""
        profile_name = self.current_profile.get()

        if profile_name == "Default":
            self.log("Default profile is always active")
            return

        profile_data = self.config.load_profile(profile_name)
        if profile_data:
            self.apply_state(profile_data)
            self.log(f"Loaded profile: {profile_name}")
            messagebox.showinfo("Success", f"Profile '{profile_name}' loaded successfully!")
        else:
            messagebox.showerror("Error", f"Profile '{profile_name}' not found")

    def delete_profile_action(self):
        """Delete a saved profile"""
        profile_name = self.current_profile.get()

        if profile_name == "Default":
            messagebox.showwarning("Cannot Delete", "Cannot delete the Default profile")
            return

        if messagebox.askyesno("Confirm Delete",
                              f"Are you sure you want to delete profile '{profile_name}'?"):
            self.config.delete_profile(profile_name)
            self.update_profile_list()
            self.current_profile.set("Default")
            self.log(f"Deleted profile: {profile_name}")
            messagebox.showinfo("Success", f"Profile '{profile_name}' deleted")

    def import_profiles_action(self):
        """Import profiles from a JSON file"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Import Profiles",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            # Ask if merge or replace
            merge = messagebox.askyesno(
                "Import Mode",
                "Merge with existing profiles?\n\nYes = Merge (keep existing)\nNo = Replace (overwrite all)"
            )

            if self.config.import_profiles(file_path, merge):
                self.update_profile_list()
                self.update_template_list()
                self.log(f"Imported profiles from: {file_path}")
                messagebox.showinfo("Success", "Profiles imported successfully!")
            else:
                messagebox.showerror("Error", "Failed to import profiles")

    def export_profiles_action(self):
        """Export all profiles to a JSON file"""
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            title="Export Profiles",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            if self.config.export_profiles(file_path):
                self.log(f"Exported profiles to: {file_path}")
                messagebox.showinfo("Success", "Profiles exported successfully!")
            else:
                messagebox.showerror("Error", "Failed to export profiles")

    def update_template_list(self):
        """Update the template dropdown with current templates"""
        template_names = ["None"] + list(self.config.get("prompt_templates", {}).keys())
        self.template_combo['values'] = template_names

    def load_template(self, event=None):
        """Load a system prompt template"""
        template_name = self.prompt_template.get()

        if template_name == "None":
            return

        templates = self.config.get("prompt_templates", {})
        if template_name in templates:
            self.system_prompt.delete('1.0', tk.END)
            self.system_prompt.insert('1.0', templates[template_name])
            self.log(f"Loaded template: {template_name}")

    def update_token_budget(self, token_count: int):
        """Update the token budget progress bar and label"""
        try:
            soft_limit = int(self.token_soft_limit.get())
            hard_limit = int(self.token_hard_limit.get())
        except ValueError:
            soft_limit = 32000
            hard_limit = 128000

        # Calculate cost (using gpt-4o as reference)
        cost, model = estimate_cost(token_count, "gpt-4o")

        # Update label
        self.token_info_label.config(text=f"{token_count:,} tokens (${cost:.4f})")

        # Update progress bar (based on hard limit)
        percentage = min(100, (token_count / hard_limit) * 100)
        self.token_progress['value'] = percentage

        # Change color based on limits (requires style configuration)
        # This is a simple visual indicator
        self.root.update_idletasks()

    def copy_to_clipboard(self):
        """Copy merged content to clipboard (Phase 1 feature)"""
        if not PYPERCLIP_AVAILABLE:
            messagebox.showerror("Error", "Clipboard functionality not available.\n"
                                         "Install pyperclip: pip install pyperclip")
            return

        # Validate settings
        if not self.folder_entries:
            messagebox.showwarning("No Folders", "Please add at least one source folder")
            return

        # Get valid folder configurations
        folder_configs = []
        for entry in self.folder_entries:
            config = entry.get_config()
            if config:
                folder_configs.append(config)

        if not folder_configs:
            messagebox.showwarning("No Folders", "Please configure at least one source folder")
            return

        # Get file extensions
        extensions = self.get_file_extensions()
        if not extensions:
            messagebox.showerror("Error", "Please specify at least one file extension")
            return

        self.log("="*60)
        self.log("Copying to clipboard...")
        self.log("="*60)

        all_content = ""
        total_tokens = 0
        total_files = 0

        # Process each folder
        for i, config in enumerate(folder_configs, 1):
            folder_path = config['folder_path']
            exclude_subfolders = config['exclude_subfolders']
            include_archive = config.get('include_archive', False)

            self.log(f"\n[{i}/{len(folder_configs)}] Processing: {folder_path}")

            # Collect files
            files, skipped = self.collect_files(folder_path, exclude_subfolders, extensions, include_archive)

            if not files:
                self.log(f"  Warning: No matching files found")
                continue

            self.log(f"  Found {len(files)} file(s)")
            total_files += len(files)

            # Create temporary output to get merged content
            temp_output = os.path.join(self.output_folder.get() or ".", "temp_clipboard.txt")
            success, content, token_count, redactions = self.merge_files(files, temp_output, folder_path)

            if success:
                all_content += content + "\n\n"
                total_tokens += token_count

                # Clean up temp file
                try:
                    os.remove(temp_output)
                except:
                    pass

        if all_content:
            try:
                pyperclip.copy(all_content)
                cost, model = estimate_cost(total_tokens, "gpt-4o")

                self.log("="*60)
                self.log(f"SUCCESS: Copied to clipboard!")
                self.log(f"Total files: {total_files}")
                self.log(f"Total tokens: {total_tokens:,}")
                self.log(f"Estimated cost: ${cost:.4f} ({model})")
                self.log("="*60)

                # Update token budget display
                self.update_token_budget(total_tokens)

                messagebox.showinfo("Copied!",
                                  f"Successfully copied {total_files} file(s) to clipboard!\n\n"
                                  f"Tokens: {total_tokens:,}\n"
                                  f"Estimated cost: ${cost:.4f} ({model})")
            except Exception as e:
                self.log(f"Error copying to clipboard: {e}")
                messagebox.showerror("Error", f"Failed to copy to clipboard:\n{e}")
        else:
            self.log("No content to copy")
            messagebox.showwarning("No Content", "No files were processed")

    def show_help(self):
        """Display help dialog with all features documentation"""
        help_dialog = tk.Toplevel(self.root)
        help_dialog.title("AI Context Assistant - Help")
        help_dialog.geometry("700x600")
        help_dialog.transient(self.root)

        # Create scrolled text widget for help content
        help_text = scrolledtext.ScrolledText(help_dialog, wrap=tk.WORD, padx=10, pady=10)
        help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Help content
        help_content = """AI CONTEXT ASSISTANT - COMPREHENSIVE FEATURE GUIDE

================================================================================
OVERVIEW
================================================================================
AI Context Assistant helps you combine multiple text files from selected folders
into single output files optimized for AI model consumption (GPT, Claude, etc.).
It includes token counting, cost estimation, PII sanitization, and advanced
filtering capabilities.

================================================================================
BASIC SETTINGS
================================================================================
• Output Folder: Select where generated files will be saved
• File Extensions: Comma-separated list of file types to include (e.g., .txt, .py, .md)
• Save Settings: Save your current configuration for future sessions

================================================================================
PHASE 1 FEATURES - Essential Processing
================================================================================
✓ PII Sanitization
  - Automatically redacts emails, API keys, passwords, and custom names
  - Configurable custom names to sanitize (e.g., usernames)
  - Shows redaction summary in logs

✓ Binary File Detection
  - Automatically skips binary files (images, executables, etc.)
  - Prevents encoding errors and reduces output size

✓ Token Counting & Cost Estimation
  - Real-time token counting using tiktoken
  - Estimated API costs for GPT-4o and other models
  - Token budget progress bar with soft/hard limits
  - Soft Limit: Warning threshold for token usage
  - Hard Limit: Maximum token budget

✓ .gitignore / .gptignore Support
  - Respects .gitignore patterns in source folders
  - .gptignore takes precedence if present
  - Helps exclude build files, dependencies, etc.

✓ Copy to Clipboard
  - Directly copy merged content to clipboard
  - Useful for quick AI queries without saving files

================================================================================
PHASE 2 FEATURES - Output Optimization
================================================================================
✓ Skeleton Mode
  - Extracts only class/function signatures from Python files
  - Reduces token usage while preserving code structure
  - Ideal for high-level code reviews and architecture discussions

✓ Directory Tree Visualization
  - Includes a visual tree structure of all processed files
  - Helps AI understand project organization

✓ Output Formats
  - Standard: Traditional delimiter-based format
  - XML: Optimized for Claude (with metadata tags)
  - Markdown: Optimized for GPT (with syntax highlighting)

✓ System Prompt Templates
  - Prepend custom instructions to your context
  - Pre-configured templates:
    * Code Review: For reviewing code quality and best practices
    * Documentation: For generating comprehensive docs
    * Refactoring: For analyzing improvement opportunities
  - Templates are included in the generated output

✓ Project Profiles/Workspaces
  - Save complete configurations as named profiles
  - Quickly switch between different project setups
  - Load/Save/Delete profiles
  - Each profile stores:
    * Source folders and their settings
    * File extensions and filters
    * All feature toggles
    * System prompts
    * Output preferences

================================================================================
PHASE 3 FEATURES - Advanced Filtering & Security
================================================================================
✓ Safe Mode
  - Automatically excludes sensitive files:
    * Environment files (.env, secrets.json, credentials.yaml)
    * SSH keys and certificates (.pem, .key, id_rsa)
    * Database files (.db, .sqlite)
    * API keys and tokens (api_keys.txt, .npmrc)
    * Shell history files
    * AWS credentials
  - Prevents accidental inclusion of secrets in AI contexts

✓ Semantic Minification
  - Removes comments and extra whitespace
  - Reduces token usage while preserving code logic
  - Supports Python, JavaScript, TypeScript, Java, C/C++, Ruby, Bash
  - Does NOT remove docstrings or code functionality

✓ Enhanced Statistics
  - Detailed file type breakdown
  - Total size in KB and bytes
  - Character and line counts
  - Average tokens per file
  - Compression ratio

✓ Profile Import/Export
  - Export all profiles to JSON file for backup
  - Import profiles from other machines or team members
  - Merge or replace existing profiles
  - Share project configurations across teams

✓ Advanced File Filtering
  - Max File Size (KB): Exclude files larger than threshold
  - Min File Size (KB): Exclude files smaller than threshold
  - Modified After (YYYY-MM-DD): Only include recently modified files
  - Useful for focusing on specific file types or recent changes

================================================================================
SOURCE FOLDERS
================================================================================
• Add up to 5 source folders
• Each folder has independent settings:
  - Exclude Subfolders: Process only root-level files
  - Include Archive Folder: Include files in "archive" directories
  - Output Name: Custom name for the generated file (timestamp auto-added)
• Browse button for easy folder selection
• Remove individual folders or clear all at once

================================================================================
WORKFLOW
================================================================================
1. Configure Basic Settings (output folder, file extensions)
2. Add one or more source folders
3. Adjust Phase 1 settings (PII sanitization, token limits, etc.)
4. Choose Phase 2 options (skeleton mode, output format, system prompt)
5. Configure Phase 3 filters (Safe Mode, file size/date filters)
6. Optionally save as a Profile for reuse
7. Click "Generate Output Files" or "Copy to Clipboard"
8. Review Status Log for processing details and statistics

================================================================================
TIPS & BEST PRACTICES
================================================================================
• Use .gptignore files in your project to exclude build artifacts
• Enable Safe Mode to prevent accidental secret exposure
• Use Skeleton Mode for large codebases to reduce token usage
• Save profiles for different use cases (code review vs documentation)
• Check token counts before sending to expensive models
• Use XML format for Claude, Markdown for GPT for optimal results
• Apply file size filters to focus on specific components
• Use System Prompt Templates to guide AI behavior

================================================================================
KEYBOARD SHORTCUTS
================================================================================
• Ctrl+S: Quick save settings (if implemented in your environment)
• Tab: Navigate between fields
• Enter: Confirm dialogs

================================================================================
TROUBLESHOOTING
================================================================================
Q: Source folders area is empty
A: Make sure you've added folders using the "Add Folder" button

Q: Token count seems high
A: Try enabling Skeleton Mode or Semantic Minification

Q: Some files are missing
A: Check if they're excluded by .gitignore/.gptignore or Safe Mode

Q: Can't see all buttons
A: Resize the window or use scrollbar for better viewing

Q: Clipboard copy not working
A: Ensure pyperclip is installed: pip install pyperclip

================================================================================
For more information, visit:
https://github.com/yourusername/ai-context-assistant
================================================================================
"""

        # Insert help content
        help_text.insert('1.0', help_content)
        help_text.config(state='disabled')  # Make read-only

        # Close button
        button_frame = ttk.Frame(help_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(button_frame, text="Close", command=help_dialog.destroy).pack(side=tk.RIGHT)

        # Center the dialog
        help_dialog.update_idletasks()
        x = (help_dialog.winfo_screenwidth() // 2) - (help_dialog.winfo_width() // 2)
        y = (help_dialog.winfo_screenheight() // 2) - (help_dialog.winfo_height() // 2)
        help_dialog.geometry(f"+{x}+{y}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = TextFileMergerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
