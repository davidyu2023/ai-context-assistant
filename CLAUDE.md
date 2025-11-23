# CLAUDE.md - AI Context Assistant Developer Guide

**Last Updated**: 2025-11-23
**For AI Assistants**: This document provides comprehensive context about the AI Context Assistant codebase structure, development workflows, and conventions to follow when contributing.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Codebase Structure](#codebase-structure)
3. [Architecture & Key Components](#architecture--key-components)
4. [Development Workflow](#development-workflow)
5. [Code Conventions & Patterns](#code-conventions--patterns)
6. [Testing Strategy](#testing-strategy)
7. [Common Development Tasks](#common-development-tasks)
8. [Important Considerations](#important-considerations)
9. [Git & Branching Strategy](#git--branching-strategy)

---

## Project Overview

### What is AI Context Assistant?

A cross-platform Python GUI application built with tkinter that combines multiple text files into optimized context files for Large Language Models (LLMs). The tool helps developers prepare code repositories and documentation for AI interactions by:

- Merging files from multiple directories with clear delimiters
- Counting tokens and estimating API costs
- Sanitizing PII and sensitive information
- Supporting multiple output formats (Standard, XML for Claude, Markdown for GPT)
- Managing project profiles and workspaces
- Providing advanced filtering and optimization features

### Tech Stack

- **Language**: Python 3.7+
- **GUI Framework**: tkinter (Python standard library)
- **Key Dependencies**:
  - `tiktoken>=0.5.0` - Token counting for GPT/Claude models
  - `pyperclip>=1.8.0` - Clipboard integration
  - `pathspec>=0.11.0` - .gitignore pattern matching
- **Build Tool**: PyInstaller (optional, for executables)
- **Testing**: Python unittest framework

### Project Phases

The application has been developed in 3 phases, each adding significant features:

**Phase 1**: Token counting, binary detection, PII sanitization, clipboard support
**Phase 2**: Project profiles, skeleton mode, directory trees, output format options
**Phase 3**: Safe mode, semantic minification, enhanced statistics, profile import/export

---

## Codebase Structure

```
ai-context-assistant/
├── text_file_merger.py          # Main application (93KB, ~2400 lines)
├── requirements.txt              # Python dependencies
├── README.md                     # User-facing documentation
├── USER_GUIDE.md                 # Detailed user guide
├── CLAUDE.md                     # This file - developer guide
│
├── test_merger.py                # Unit tests for core merging functionality
├── test_phase1.py                # Phase 1 feature tests
├── test_phase1_simple.py         # Simplified Phase 1 tests
├── test_phase2.py                # Phase 2 feature tests
├── test_phase2_standalone.py     # Standalone Phase 2 tests
├── test_phase3_standalone.py     # Standalone Phase 3 tests
│
├── create_test_data.py           # Test data generation script
├── test_data/                    # Test data for development
│   ├── project1/                 # Sample project 1
│   └── project2/                 # Sample project 2
│
├── build_executable.bat          # Windows build script
├── build_executable.sh           # Unix build script
├── run_ai_context_assistant.bat  # Windows launcher
│
├── .gitignore                    # Git ignore patterns
├── .gptignore.example            # Example ignore file for the tool
│
└── config.json                   # Runtime configuration (auto-generated, gitignored)
```

### File Locations by Purpose

| Purpose | Files |
|---------|-------|
| Main Application | `text_file_merger.py` |
| User Documentation | `README.md`, `USER_GUIDE.md` |
| Developer Documentation | `CLAUDE.md` (this file) |
| Testing | `test_*.py`, `create_test_data.py`, `test_data/` |
| Configuration | `config.json` (auto-generated), `.gitignore`, `.gptignore.example` |
| Build/Deploy | `build_executable.bat`, `build_executable.sh`, `run_ai_context_assistant.bat` |

---

## Architecture & Key Components

### Main Application Structure (`text_file_merger.py`)

The application is organized into clear sections with ~2400 lines of code:

#### 1. **Imports & Dependencies** (Lines 1-60)
- Conditional imports with graceful degradation
- Sets flags: `TIKTOKEN_AVAILABLE`, `PYPERCLIP_AVAILABLE`, `PATHSPEC_AVAILABLE`

#### 2. **Phase 1 Utility Functions** (Lines 62-200)
```python
is_binary_file(file_path: Path) -> bool
sanitize_pii(content: str, custom_names: List[str]) -> Tuple[str, List[str]]
count_tokens(text: str, model: str) -> int
estimate_cost(token_count: int, model: str) -> Tuple[float, str]
```

#### 3. **Phase 2 Utility Functions** (Lines 202-470)
```python
extract_skeleton(file_path: Path) -> Optional[str]  # AST-based Python signature extraction
generate_directory_tree(folder_path: Path, files: List[Path], prefix: str) -> str
format_as_xml(files_data: List[Dict], metadata: Dict) -> str
format_as_markdown(files_data: List[Dict], metadata: Dict) -> str
```

#### 4. **Phase 3 Utility Functions** (Lines 472-635)
```python
is_safe_mode_excluded(file_path: Path) -> bool  # 28 sensitive file patterns
semantic_minify(content: str, language: str) -> str  # Comment removal, ~40% reduction
calculate_statistics(files: List[Path], content: str, token_count: int) -> Dict
filter_files_by_criteria(files: List[Path], max_size_kb, min_size_kb, modified_after) -> Tuple
```

#### 5. **Config Class** (Lines 637-781)
Handles persistent configuration storage using JSON:
- `load()` - Load config from disk
- `save(config_dict)` - Persist configuration
- `get(key, default)` - Retrieve config values
- `set(key, value)` - Update config values

#### 6. **AddFolderDialog Class** (Lines 783-876)
Modal dialog for adding source folders:
- Browse for folder
- Set output filename
- Toggle subfolder inclusion
- Toggle archive folder exclusion

#### 7. **TextFileMergerApp Class** (Lines 878-2370)
Main application window with sections:

**Initialization & UI Setup**:
- `__init__()` - Initialize app and load config
- `create_widgets()` - Build complete UI layout
- `create_output_section()` - Output folder and extensions
- `create_source_folders_section()` - Folder management UI
- `create_phase1_section()` - Token counting, PII, clipboard
- `create_phase2_section()` - Profiles, skeleton mode, formats
- `create_phase3_section()` - Safe mode, statistics, filters
- `create_action_buttons()` - Generate, Copy, Help, Settings
- `create_status_section()` - Status log with scrollbar

**Core Functionality**:
- `generate_output_files()` - Main file merging logic
- `copy_to_clipboard()` - Clipboard integration
- `process_files()` - File collection and filtering
- `merge_files_content()` - Content aggregation

**Profile Management**:
- `save_profile()` - Save current configuration as profile
- `load_profile()` - Restore profile settings
- `delete_profile()` - Remove saved profile
- `export_profiles()` / `import_profiles()` - Profile portability

**Folder Management**:
- `open_folder_dialog()` - Popup dialog for managing folders
- `add_folder()` - Add new source folder
- `edit_folder()` - Modify existing folder
- `delete_folder()` - Remove folder from list
- `save_folders_and_close()` - Persist folder configuration

**Helper Methods**:
- `log()` - Append messages to status log
- `save_settings()` - Persist current configuration
- `load_settings()` - Restore previous session
- `show_help()` - Display help dialog
- `update_token_progress()` - Update token usage UI

#### 8. **Main Entry Point** (Lines 2373-2381)
```python
def main():
    root = tk.Tk()
    app = TextFileMergerApp(root)
    root.mainloop()
```

### Key Design Patterns

1. **Graceful Degradation**: Optional dependencies checked with try/except
2. **Configuration Persistence**: JSON-based config with auto-save
3. **Separation of Concerns**: Utility functions separate from UI logic
4. **Modular Phases**: Each feature phase has dedicated sections
5. **Progressive Enhancement**: Features can be toggled independently

---

## Development Workflow

### Setting Up Development Environment

```bash
# Clone repository
git clone <repository-url>
cd ai-context-assistant

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python text_file_merger.py
```

### Running Tests

```bash
# Run all tests
python -m unittest discover -s . -p "test_*.py"

# Run specific test file
python test_phase1.py
python test_phase2_standalone.py
python test_phase3_standalone.py

# Generate test data
python create_test_data.py
```

### Building Executable

```bash
# Windows
.\build_executable.bat

# Unix/Linux/Mac
chmod +x build_executable.sh
./build_executable.sh

# Manual build
pip install pyinstaller
pyinstaller --onefile --windowed text_file_merger.py
# Executable created in dist/text_file_merger.exe
```

### Configuration Management

The application auto-generates `config.json` in the application directory. This file is gitignored to avoid committing user-specific settings.

**Important**: Never hardcode paths or user-specific values in the source code. Always use the `Config` class for persistence.

---

## Code Conventions & Patterns

### Python Style Guidelines

1. **Docstrings**: All functions should have docstrings with Args and Returns
   ```python
   def example_function(param: str) -> int:
       """
       Brief description of function.

       Args:
           param: Description of parameter

       Returns:
           Description of return value
       """
       pass
   ```

2. **Type Hints**: Use type hints for function signatures
   ```python
   def process_file(file_path: Path, options: Dict[str, bool]) -> Tuple[str, int]:
       pass
   ```

3. **Imports**: Organize imports in groups
   - Standard library imports
   - Third-party imports (with try/except for optional ones)
   - Local imports

4. **Line Length**: Aim for 100 characters, maximum 120

5. **Naming Conventions**:
   - Functions/methods: `snake_case`
   - Classes: `PascalCase`
   - Constants: `UPPER_SNAKE_CASE`
   - Private methods: `_leading_underscore`

### UI/tkinter Conventions

1. **Widget Creation**: Group related widgets in methods
   ```python
   def create_phase3_section(self):
       frame = ttk.LabelFrame(self.phase3_features_frame, text="Phase 3 Features")
       frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
       # Add widgets...
   ```

2. **Grid Layout**: Use grid() for precise control, pack() for simple stacking

3. **Variable Naming**: Use `tk.StringVar()`, `tk.BooleanVar()`, `tk.IntVar()` for UI bindings
   - Name as: `self.var_feature_name = tk.BooleanVar(value=True)`

4. **Frames**: Use `ttk.LabelFrame` for grouped sections with headers

5. **Status Logging**: Always use `self.log(message)` instead of print()

### Error Handling

1. **File Operations**: Wrap in try/except with user-friendly error messages
   ```python
   try:
       with open(file_path, 'r', encoding='utf-8') as f:
           content = f.read()
   except Exception as e:
       self.log(f"Error reading {file_path}: {e}")
       return None
   ```

2. **User Notifications**: Use `messagebox` for errors, `self.log()` for status
   ```python
   messagebox.showerror("Error", "Failed to save configuration")
   self.log("Error: Could not write to config.json")
   ```

3. **Graceful Degradation**: Check feature flags before using optional features
   ```python
   if TIKTOKEN_AVAILABLE:
       tokens = count_tokens(content)
   else:
       tokens = len(content) // 4  # Fallback approximation
   ```

### File Processing Patterns

**Standard File Processing Loop**:
```python
for file_path in files:
    # 1. Check if should skip
    if self.var_skip_binary.get() and is_binary_file(file_path):
        self.log(f"Skipped (binary): {file_path.name}")
        continue

    # 2. Check safe mode
    if self.var_safe_mode.get() and is_safe_mode_excluded(file_path):
        self.log(f"Skipped (Safe Mode): {file_path.name}")
        continue

    # 3. Read file
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        self.log(f"Error reading {file_path.name}: {e}")
        continue

    # 4. Apply transformations
    if self.var_pii_sanitization.get():
        content, redactions = sanitize_pii(content, custom_names)

    if self.var_semantic_minify.get():
        content = semantic_minify(content, language)

    # 5. Process content
    # ...
```

---

## Testing Strategy

### Test File Organization

| Test File | Purpose | Coverage |
|-----------|---------|----------|
| `test_merger.py` | Core file merging functionality | Basic operations |
| `test_phase1.py` | Token counting, PII, binary detection | Phase 1 features |
| `test_phase1_simple.py` | Simplified Phase 1 tests | Quick validation |
| `test_phase2.py` | Skeleton mode, profiles, formats | Phase 2 features |
| `test_phase2_standalone.py` | Standalone Phase 2 tests | Independent testing |
| `test_phase3_standalone.py` | Safe mode, statistics, filters | Phase 3 features |

### Test Data Generation

The `create_test_data.py` script generates sample project structures in `test_data/`:
- `project1/` - Python files with subfolders
- `project2/` - Mixed file types, scripts, docs

**Regenerate test data**:
```bash
python create_test_data.py
```

### Running Specific Tests

```bash
# Test token counting
python test_phase1_simple.py

# Test skeleton mode
python test_phase2_standalone.py

# Test safe mode and statistics
python test_phase3_standalone.py
```

### Manual Testing Checklist

When making changes, verify:

- [ ] Application launches without errors
- [ ] Config saves and loads correctly
- [ ] Folder dialog opens and closes properly
- [ ] Generate button creates output files
- [ ] Copy to clipboard works (if pyperclip available)
- [ ] Token counting displays correctly (if tiktoken available)
- [ ] PII sanitization redacts expected patterns
- [ ] Profile save/load preserves all settings
- [ ] Each phase's features toggle correctly
- [ ] Status log updates with appropriate messages
- [ ] Help dialog displays complete information

---

## Common Development Tasks

### Adding a New Feature

1. **Determine Phase**: Identify which phase the feature belongs to (or create Phase 4)

2. **Add Utility Function** (if needed):
   ```python
   # Add to appropriate utility section
   def new_feature_function(param: str) -> str:
       """
       Description of new feature.

       Args:
           param: Input parameter

       Returns:
           Processed result
       """
       # Implementation
       pass
   ```

3. **Add UI Controls**:
   ```python
   def create_phase4_section(self):
       frame = ttk.LabelFrame(self.main_frame, text="Phase 4 Features")
       frame.grid(row=X, column=0, padx=10, pady=5, sticky="ew")

       self.var_new_feature = tk.BooleanVar(value=False)
       ttk.Checkbutton(frame, text="Enable New Feature",
                      variable=self.var_new_feature).grid(row=0, column=0)
   ```

4. **Integrate into Processing**:
   ```python
   # In generate_output_files() or relevant method
   if self.var_new_feature.get():
       content = new_feature_function(content)
   ```

5. **Add to Config**:
   ```python
   # In save_settings()
   config.set('enable_new_feature', self.var_new_feature.get())

   # In load_settings()
   self.var_new_feature.set(config.get('enable_new_feature', False))
   ```

6. **Write Tests**:
   ```python
   # Create test_phase4.py or add to existing test file
   def test_new_feature(self):
       result = new_feature_function("test input")
       self.assertEqual(result, "expected output")
   ```

7. **Update Documentation**:
   - Add feature description to README.md
   - Update USER_GUIDE.md with usage instructions
   - Update this CLAUDE.md if architecture changes

### Modifying Existing Features

1. **Locate the code**: Use grep or search for relevant function/class names
   ```bash
   grep -n "function_name" text_file_merger.py
   ```

2. **Understand dependencies**: Check what calls the function and what it calls

3. **Make changes**: Update implementation with proper error handling

4. **Update tests**: Modify existing tests or add new test cases

5. **Test thoroughly**: Run related test files and manual testing

6. **Update docs**: Reflect changes in README.md and USER_GUIDE.md

### Fixing Bugs

1. **Reproduce the bug**: Create a minimal test case

2. **Locate the issue**: Use status log messages and print debugging
   ```python
   self.log(f"DEBUG: Variable value = {value}")
   ```

3. **Implement fix**: Make targeted changes, avoid over-engineering

4. **Add regression test**: Ensure bug doesn't return
   ```python
   def test_bug_fix_issue_123(self):
       # Test that reproduces the original bug
       # and verifies the fix works
       pass
   ```

5. **Verify side effects**: Test related functionality still works

### Adding Support for New File Types

To add a new language for semantic minification:

1. **Add comment patterns**:
   ```python
   # In semantic_minify() function
   comment_patterns = {
       'python': [(r'#.*$', '')],
       'javascript': [(r'//.*$', '')],
       'yournewlang': [(r'yourlang_comment_pattern', '')]
   }
   ```

2. **Map file extensions**:
   ```python
   # In semantic_minify() or caller
   extension_to_lang = {
       '.py': 'python',
       '.js': 'javascript',
       '.yourlang': 'yournewlang'
   }
   ```

3. **Test with sample files**: Create test file in `test_data/`

4. **Update documentation**: Add to supported languages list

---

## Important Considerations

### Security & Privacy

1. **PII Sanitization**: Always test with real-looking sample data
   - Email patterns: `user@example.com`
   - API keys: Use patterns from actual providers
   - Usernames: Test custom name replacement

2. **Safe Mode**: 28 sensitive file patterns defined in `is_safe_mode_excluded()`
   - Environment files (.env, .env.local)
   - SSH keys (id_rsa, id_dsa, id_ed25519)
   - Certificates (*.pem, *.key, *.p12)
   - Database files (*.db, *.sqlite)
   - Credentials (credentials.json, .aws/credentials)

3. **Binary File Detection**: Uses null byte detection (`\x00` in first 1KB)

4. **File Access**: Always use `encoding='utf-8', errors='ignore'` to handle encoding issues

### Performance Considerations

1. **Large Files**:
   - Skeleton mode reduces Python files by ~92%
   - Semantic minification reduces ~40%
   - Consider max file size filters

2. **Token Counting**:
   - Can be slow for very large content
   - Uses cl100k_base encoding (GPT-4/3.5-turbo compatible)
   - Fallback: `len(text) // 4` if tiktoken unavailable

3. **Directory Trees**:
   - Generated on-the-fly from included files
   - Minimal performance impact

4. **UI Responsiveness**:
   - Long operations should update status log
   - Consider threading for very large operations (future enhancement)

### Cross-Platform Compatibility

1. **Path Handling**: Always use `Path` from `pathlib`
   ```python
   from pathlib import Path
   file_path = Path(directory) / filename
   ```

2. **Line Endings**: Python handles automatically with text mode

3. **tkinter**: Generally consistent, test on target platforms

4. **Clipboard**: `pyperclip` handles platform differences

### Configuration Management

1. **Config File Location**: Same directory as script
   ```python
   config_file = Path(__file__).parent / "config.json"
   ```

2. **Default Values**: Always provide defaults in `config.get(key, default)`

3. **Migration**: When adding new config keys, ensure backward compatibility

4. **Validation**: Validate config values before using
   ```python
   max_size = config.get('max_file_size_kb', None)
   if max_size is not None and max_size < 0:
       max_size = None  # Invalid, use no limit
   ```

### Code Maintenance

1. **Avoid Duplication**: Extract common patterns into utility functions

2. **Keep Phases Separate**: Don't mix Phase 1/2/3 logic unnecessarily

3. **Comment Complex Logic**: Especially regex patterns and AST parsing

4. **Status Logging**: Log important operations for debugging
   ```python
   self.log(f"Processing {len(files)} files...")
   self.log(f"Generated output: {output_file}")
   ```

5. **Error Messages**: Make them actionable
   - Bad: "Error occurred"
   - Good: "Could not read file.txt: Permission denied"

---

## Git & Branching Strategy

### Branch Naming

This project uses a specific branch naming convention:

- Feature branches: `claude/<descriptive-name>-<session-id>`
- Example: `claude/claude-md-mic0hi1zumars83m-0147Fjm5CB8EitsKhkMbXhgF`

**CRITICAL**: Branches must start with `claude/` and end with matching session ID, otherwise push will fail with 403 error.

### Commit Message Format

Follow conventional commit style:

```
<type>: <brief description>

<detailed description if needed>

- Specific change 1
- Specific change 2
```

**Types**: feat, fix, docs, style, refactor, test, chore

**Examples**:
```
feat: Add semantic minification for Python files

- Implements comment removal using regex
- Reduces token count by ~40% on average
- Preserves code functionality and indentation

fix: Handle encoding errors when reading text files

Use errors='ignore' parameter to prevent crashes
when encountering invalid UTF-8 sequences

docs: Update README with Phase 3 features

- Add Safe Mode documentation
- Document profile import/export
- Update examples with new filters
```

### Pull Request Workflow

1. **Create feature branch** following naming convention
2. **Make changes** with clear, focused commits
3. **Test thoroughly** - run test suite and manual tests
4. **Update documentation** - README, USER_GUIDE, CLAUDE.md
5. **Push to remote** with `-u` flag:
   ```bash
   git push -u origin claude/your-branch-name-session-id
   ```
6. **Create PR** with comprehensive description:
   - Summary of changes
   - Testing performed
   - Screenshots if UI changes
   - Related issues

### Merge Strategy

- **Squash and merge** for feature branches
- Maintain clean main branch history
- Delete branch after merge

### Recent Development History

Recent work has focused on UI improvements:
- Reorganizing Help and Save Settings buttons (323e776)
- Auto-saving folder list changes (6a45227)
- Popup dialog for source folders with table view (f9acb08)
- Enhanced Help dialog with comprehensive guide (2666f48)

---

## Debugging Tips

### Common Issues & Solutions

**Issue**: tkinter window doesn't appear
- **Solution**: Check if `root.mainloop()` is called in `main()`

**Issue**: Config not saving
- **Solution**: Verify `config.json` is not read-only, check file permissions

**Issue**: Token count shows 0 or incorrect
- **Solution**: Verify tiktoken is installed: `pip install tiktoken>=0.5.0`

**Issue**: Clipboard copy doesn't work
- **Solution**: Install pyperclip: `pip install pyperclip>=1.8.0`

**Issue**: Files not being found
- **Solution**: Check file extension filter, verify paths are absolute

**Issue**: PII not being redacted
- **Solution**: Enable PII sanitization checkbox, check custom names in config

### Debugging Tools

1. **Status Log**: Primary debugging output
   ```python
   self.log(f"DEBUG: Processing file {file_path}")
   self.log(f"DEBUG: Token count = {tokens}")
   ```

2. **Config Inspection**: Check `config.json` in app directory

3. **Test Data**: Use `create_test_data.py` to generate known test cases

4. **Python Debugger**:
   ```python
   import pdb; pdb.set_trace()  # Add breakpoint
   ```

### Logging Best Practices

- Log user actions: "Generating output files..."
- Log errors with context: "Error reading file.txt: [Errno 2] No such file"
- Log statistics: "Processed 15 files, 1,234 tokens"
- Log warnings: "Soft token limit exceeded (35,000 / 32,000)"
- Don't log sensitive data (file contents, PII)

---

## Additional Resources

### Key Files to Reference

- **README.md**: User-facing feature documentation
- **USER_GUIDE.md**: Detailed usage instructions
- **requirements.txt**: Dependency versions
- **.gptignore.example**: Example patterns for ignoring files

### External Documentation

- [tkinter documentation](https://docs.python.org/3/library/tkinter.html)
- [tiktoken GitHub](https://github.com/openai/tiktoken)
- [pathspec documentation](https://python-path-specification.readthedocs.io/)
- [PyInstaller manual](https://pyinstaller.org/en/stable/)

### Development Philosophy

This project follows these principles:

1. **User-Friendly**: Prioritize ease of use over complexity
2. **Reliable**: Graceful error handling, no crashes
3. **Transparent**: Clear status messages and logging
4. **Efficient**: Optimize for token reduction and cost savings
5. **Secure**: Protect sensitive information by default
6. **Portable**: Work across platforms with minimal dependencies
7. **Maintainable**: Clean code, clear structure, good documentation

---

## Contributing Guidelines

When contributing to this project:

1. **Understand the context**: Read this CLAUDE.md thoroughly
2. **Follow conventions**: Match existing code style and patterns
3. **Test comprehensively**: Unit tests + manual testing
4. **Document thoroughly**: Update all relevant docs
5. **Communicate clearly**: Descriptive commits and PR descriptions
6. **Preserve backward compatibility**: Don't break existing configs
7. **Consider edge cases**: Encoding errors, missing files, invalid inputs
8. **Ask questions**: If uncertain, ask before implementing

---

## Version History & Roadmap

### Current State (Phase 3 Complete)

- ✅ Core file merging with delimiters
- ✅ Token counting and cost estimation
- ✅ PII sanitization and Safe Mode
- ✅ Binary detection and .gitignore support
- ✅ Clipboard integration
- ✅ Project profiles and workspaces
- ✅ Skeleton mode (92% token reduction)
- ✅ Multiple output formats (Standard, XML, Markdown)
- ✅ Directory tree visualization
- ✅ System prompt templates
- ✅ Enhanced statistics and analytics
- ✅ Profile import/export
- ✅ Advanced filtering (size, date)
- ✅ Semantic minification (40% reduction)

### Potential Future Enhancements (Phase 4+)

- 🔲 Batch processing multiple profiles
- 🔲 Custom sanitization rules (user-defined regex)
- 🔲 Diff-based context (only changed files)
- 🔲 Git integration (branch comparison)
- 🔲 Cloud storage integration (Google Drive, Dropbox)
- 🔲 API endpoint for programmatic access
- 🔲 Multi-threading for large projects
- 🔲 Syntax highlighting in preview
- 🔲 Token budget optimization suggestions
- 🔲 LLM-specific optimizations per model

---

## Quick Reference

### Most Common Tasks

```bash
# Run application
python text_file_merger.py

# Run tests
python -m unittest discover -s . -p "test_*.py"

# Build executable
pyinstaller --onefile --windowed text_file_merger.py

# Create test data
python create_test_data.py
```

### Key Functions by Use Case

| Use Case | Function(s) | Location |
|----------|------------|----------|
| Token counting | `count_tokens()` | text_file_merger.py:149 |
| PII redaction | `sanitize_pii()` | text_file_merger.py:84 |
| Binary detection | `is_binary_file()` | text_file_merger.py:66 |
| Skeleton extraction | `extract_skeleton()` | text_file_merger.py:202 |
| Directory tree | `generate_directory_tree()` | text_file_merger.py:290 |
| Safe mode check | `is_safe_mode_excluded()` | text_file_merger.py:472 |
| Comment removal | `semantic_minify()` | text_file_merger.py:498 |
| Statistics | `calculate_statistics()` | text_file_merger.py:547 |
| File filtering | `filter_files_by_criteria()` | text_file_merger.py:590 |

### Configuration Keys

```json
{
  "output_folder": "string - path to output directory",
  "file_extensions": "string - comma-separated extensions",
  "enable_pii_sanitization": "boolean - redact sensitive info",
  "custom_sanitize_names": "array - custom names to redact",
  "target_model": "string - gpt-4o|gpt-4o-mini|claude-3.5-sonnet|claude-3-opus",
  "token_soft_limit": "integer - warning threshold",
  "token_hard_limit": "integer - maximum tokens",
  "respect_gitignore": "boolean - use .gitignore patterns",
  "enable_skeleton_mode": "boolean - extract signatures only",
  "output_format": "string - standard|xml|markdown",
  "show_directory_tree": "boolean - include tree visualization",
  "system_prompt": "string - custom prompt/instructions",
  "current_profile": "string - active profile name",
  "enable_safe_mode": "boolean - exclude sensitive files",
  "enable_semantic_minify": "boolean - remove comments",
  "show_statistics": "boolean - display analytics",
  "max_file_size_kb": "integer|null - max file size",
  "min_file_size_kb": "integer|null - min file size",
  "modified_after": "string|null - YYYY-MM-DD format"
}
```

---

**End of CLAUDE.md** - This document should be updated whenever significant architectural changes are made to the codebase.
