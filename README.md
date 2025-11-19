# AI Context Assistant - Text File Merger

A Windows GUI application for combining multiple text files into a single file, making it easier to include them as attachments for AI prompts.

## Features

- **GUI Interface**: User-friendly Windows interface built with tkinter
- **Multiple Folder Support**: Process up to 5 source folders simultaneously
- **Subfolder Control**: Option to exclude nested subfolders during processing
- **File Extension Filtering**: Specify which file extensions to include (e.g., .txt, .py, .md)
- **Persistent Settings**: Remembers your output folder and file extension preferences
- **Timestamped Output**: Automatically adds timestamps to output filenames
- **Clear File Markers**: Each source file is clearly marked with begin/end delimiters in the output

## Requirements

- Python 3.7 or higher
- tkinter (usually included with Python on Windows)

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

## Usage

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

## Output Format

Each output file contains all text files from the source folder with clear delimiters:

```
================================================================================
BEGIN FILE: path/to/file.txt
================================================================================
[file content here]
================================================================================
END FILE: path/to/file.txt
================================================================================
```

## Configuration

Settings are automatically saved to `config.json` in the application directory and include:
- Last used output folder path
- Preferred file extensions

## Building Executable (Optional)

To create a standalone Windows executable:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed text_file_merger.py
```

The executable will be created in the `dist` folder.

## License

MIT License
