# AI Context Assistant - Text File Merger

A cross-platform GUI application for combining multiple text files into a single file optimized for AI prompts, with advanced features for token counting, cost estimation, PII sanitization, and more.

## Features

### Core Features
- **GUI Interface**: User-friendly interface built with tkinter
- **Multiple Folder Support**: Process up to 5 source folders simultaneously
- **Subfolder Control**: Option to exclude nested subfolders during processing
- **File Extension Filtering**: Specify which file extensions to include (e.g., .txt, .py, .md)
- **Persistent Settings**: Remembers your output folder and file extension preferences
- **Timestamped Output**: Automatically adds timestamps to output filenames
- **Clear File Markers**: Each source file is clearly marked with begin/end delimiters in the output

### Phase 1 Features

#### 🎯 Token Counting & Cost Estimation
- **Real-time Token Counting**: Uses `tiktoken` for accurate token counting compatible with GPT-4, GPT-3.5-turbo, and Claude models
- **Cost Calculator**: Displays estimated API costs based on current pricing for different models
- **Visual Token Budget**: Progress bar showing token usage against configurable soft/hard limits
- **Model Selection**: Choose target model (GPT-4o, GPT-4o-mini, Claude 3.5 Sonnet, Claude 3 Opus)

#### 🔒 Security & Privacy
- **PII Sanitization**: Automatically redacts emails, usernames, and sensitive information
- **Custom Name Redaction**: Replace specific names/usernames (e.g., "davidyu", "david yu") with placeholders
- **API Key Detection**: Identifies and redacts common API key patterns (OpenAI, AWS, Slack, GitHub)
- **Password Protection**: Detects and redacts password assignments in code

#### 🚫 Smart File Filtering
- **Binary File Detection**: Automatically skips binary files (images, executables, etc.)
- **.gitignore/.gptignore Support**: Respects ignore patterns from `.gitignore` or `.gptignore` files
- **Archive Folder Exclusion**: Option to exclude archive folders from processing
- **Detailed Skip Reports**: Shows which files were skipped and why

#### 📋 Clipboard Integration
- **Copy to Clipboard**: One-click copy of merged content directly to clipboard
- **Toast Notifications**: Shows token count and cost when copying
- **No Intermediate Files**: Skip file generation and paste directly into AI chat

### Phase 2 Features (NEW!)

#### 🎨 Project Profiles & Workspaces
- **Save/Load Profiles**: Save complete configurations including folders, settings, and prompts
- **Quick Context Switching**: Switch between different projects instantly
- **Profile Management**: Create, load, and delete custom profiles
- **Persistent Workspaces**: Each profile remembers all settings and source folders

#### 🔧 Skeleton Mode (Code Structure Extraction)
- **91.9% Token Reduction**: Extract only class/function signatures from Python files
- **Smart AST Parsing**: Uses Python's AST module for accurate code analysis
- **Preserves Documentation**: Keeps docstrings while removing implementation details
- **Automatic Fallback**: Falls back to full content if extraction fails
- **Perfect for Architecture Review**: Ideal for understanding code structure without implementation noise

#### 📊 Enhanced Metadata & Visualization
- **Directory Tree**: Auto-generated tree structure showing project organization
- **File Statistics**: Comprehensive metadata including file count, timestamps, and settings
- **Visual Organization**: Clear hierarchy display for better context understanding

#### 📝 System Prompt Templates
- **Reusable Instructions**: Save and load custom system prompts
- **Built-in Templates**: Pre-configured templates for Code Review, Documentation, and Refactoring
- **Quick Loading**: Select template from dropdown to instantly populate prompt
- **Custom Templates**: Create your own prompt templates for specific workflows

#### 🎯 Model-Specific Output Formats
- **Standard Format**: Classic delimiter-based format with enhanced metadata
- **XML Format**: Optimized for Claude models with structured `<document>` tags
- **Markdown Format**: Optimized for GPT models with syntax-highlighted code blocks
- **Automatic Language Detection**: Smart syntax highlighting based on file extensions

## Requirements

- Python 3.7 or higher
- tkinter (usually included with Python on Windows and most Linux distributions)
- tiktoken (for token counting)
- pyperclip (for clipboard support)
- pathspec (for .gitignore support)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd ai-context-assistant
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

The required packages are:
- `tiktoken>=0.5.0` - Token counting for various LLM models
- `pyperclip>=1.8.0` - Clipboard integration
- `pathspec>=0.11.0` - .gitignore/.gptignore pattern matching

## Usage

### Basic Usage

1. Run the application:
```bash
python text_file_merger.py
```

2. Configure your settings:
   - Set the output folder where merged files will be saved
   - Specify file extensions to include (comma-separated, e.g., `.txt, .py, .md`)

3. Add source folders:
   - Click "Add Folder" to select a source folder
   - Choose whether to include or exclude subfolders
   - Provide a name for the output file
   - Repeat to add up to 5 folders

4. Click "Generate Output Files" to create the merged files

### Phase 1 Features Usage

#### Token Budget Configuration
1. Select your **Target Model** from the dropdown (GPT-4o, GPT-4o-mini, Claude 3.5 Sonnet, etc.)
2. Set **Soft Limit** (warning threshold) and **Hard Limit** (maximum tokens)
3. The progress bar will show real-time token usage and estimated costs

#### PII Sanitization
1. Check **"Enable PII Sanitization"** to automatically redact sensitive information
2. Default redactions include:
   - Emails (e.g., `user@example.com` → `<EMAIL_ADDRESS>`)
   - Usernames (e.g., `davidyu`, `david yu` → `<USER_1>`, `<USER_2>`)
   - API keys (OpenAI, AWS, Slack, GitHub)
   - Password assignments in code
3. Custom names can be configured in `config.json`

#### Smart File Filtering
1. Check **"Skip Binary Files"** to automatically exclude images, executables, etc.
2. Check **"Respect .gitignore/.gptignore"** to use ignore patterns
3. Create a `.gptignore` file in your project root (see `.gptignore.example`)
4. Archive folders can be excluded/included per folder

#### Clipboard Integration
1. Configure your folders and settings as usual
2. Click **"Copy to Clipboard"** instead of "Generate Output Files"
3. Content is copied directly to clipboard with token count and cost displayed
4. Paste directly into ChatGPT, Claude, or any AI chat interface

### Phase 2 Features Usage

#### Project Profiles & Workspaces
1. Configure your folders, settings, and system prompt for a specific project
2. Click **"Save As..."** in the Profile section
3. Enter a profile name (e.g., "Backend API", "Frontend UI", "Documentation")
4. To load a saved profile:
   - Select it from the Profile dropdown
   - Click **"Load"**
5. All settings, folders, and prompts are restored instantly!

#### Skeleton Mode
1. Check **"Skeleton Mode (signatures only)"** in Phase 2 Features
2. This applies **only to Python (.py) files**
3. Generates output files for other types
4. Achieves ~92% token reduction while preserving structure
5. Perfect for:
   - Understanding code architecture
   - Reviewing class hierarchies
   - Analyzing API surfaces
   - Planning refactoring

**Example Output:**
```python
class Config:
    """Handles persistent configuration storage"""
    def __init__(self, config_file: str):
        ...

    def load(self) -> dict:
        """Load configuration from file"""
        ...
```

#### Directory Tree Visualization
1. Check **"Show Directory Tree"** (enabled by default)
2. A visual tree structure is automatically included in the output header
3. Shows the organization of all included files
4. Example:
```
ai-context-assistant/
├── src/
│   ├── utils/
│   │   └── helper.py
│   └── main.py
└── tests/
    └── test_main.py
```

#### System Prompt Templates
1. Use the **Template** dropdown to select a pre-configured prompt:
   - **Code Review**: For reviewing code quality and best practices
   - **Documentation**: For generating comprehensive documentation
   - **Refactoring**: For analyzing and improving code structure
2. The template text is loaded into the System Prompt area
3. Edit as needed or write your own custom prompt
4. The system prompt is prepended to all generated output

#### Output Formats
1. Select format from **Output Format** dropdown:
   - **standard**: Classic format with clear delimiters (default)
   - **xml**: Optimized for Claude models with XML structure
   - **markdown**: Optimized for GPT models with Markdown formatting

2. **XML Format** (Best for Claude):
```xml
<?xml version='1.0' encoding='UTF-8'?>
<context>
  <metadata>
    <generated_by>AI Context Assistant</generated_by>
    <timestamp>2025-11-23 14:30:00</timestamp>
  </metadata>
  <documents>
    <document index='1'>
      <source>project/file.py</source>
      <document_content>...</document_content>
    </document>
  </documents>
</context>
```

3. **Markdown Format** (Best for GPT):
```markdown
# AI Context

## Metadata
- **Generated By**: AI Context Assistant
- **Timestamp**: 2025-11-23 14:30:00

## Files

### File: `project/file.py`

\```python
# code here
\```
```

## Output Format

Each output file contains metadata and all text files from the source folder with clear delimiters:

```
Generated by AI Context Assistant
Timestamp: 2025-11-23 14:30:00
Total files: 15
Target Model: gpt-4o
PII Sanitization: ENABLED

================================================================================

================================================================================
BEGIN FILE: project_name/path/to/file.txt
================================================================================
[file content here - with PII redacted if enabled]
================================================================================
END FILE: project_name/path/to/file.txt
================================================================================
```

## Configuration

Settings are automatically saved to `config.json` in the application directory and include:

### Basic Settings
- Last used output folder path
- Preferred file extensions
- Source folder configurations

### Phase 1 Settings
- `enable_pii_sanitization`: Enable/disable PII redaction (default: `true`)
- `custom_sanitize_names`: List of custom names to redact (default: `["davidyu", "david yu"]`)
- `target_model`: Target LLM model for token counting (default: `"gpt-4o"`)
- `enable_binary_detection`: Skip binary files (default: `true`)
- `token_soft_limit`: Warning threshold in tokens (default: `32000`)
- `token_hard_limit`: Maximum token limit (default: `128000`)
- `respect_gitignore`: Use .gitignore/.gptignore patterns (default: `true`)

### Phase 2 Settings
- `enable_skeleton_mode`: Extract only class/function signatures from Python files (default: `false`)
- `output_format`: Output format - "standard", "xml", or "markdown" (default: `"standard"`)
- `show_directory_tree`: Include directory tree visualization (default: `true`)
- `system_prompt`: Custom system prompt/instructions (default: `""`)
- `current_profile`: Currently active profile (default: `"Default"`)
- `profiles`: Dictionary of saved project profiles
- `prompt_templates`: Dictionary of reusable system prompt templates

### Example config.json
```json
{
  "output_folder": "/path/to/output",
  "file_extensions": ".txt, .py, .md, .json",
  "enable_pii_sanitization": true,
  "custom_sanitize_names": ["davidyu", "david yu", "mycompany"],
  "target_model": "gpt-4o",
  "token_soft_limit": 32000,
  "token_hard_limit": 128000,
  "respect_gitignore": true,
  "enable_skeleton_mode": false,
  "output_format": "standard",
  "show_directory_tree": true,
  "system_prompt": "You are a senior software engineer...",
  "current_profile": "Backend API",
  "profiles": {
    "Backend API": {
      "output_folder": "/projects/backend/context",
      "source_folders": [...],
      "system_prompt": "Review this backend API code..."
    },
    "Frontend UI": {
      "output_folder": "/projects/frontend/context",
      "source_folders": [...],
      "system_prompt": "Analyze this React application..."
    }
  }
}
```

## Building Executable (Optional)

To create a standalone Windows executable:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed text_file_merger.py
```

The executable will be created in the `dist` folder.

## License

MIT License
