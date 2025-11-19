#!/bin/bash

# Build script for creating executable (Linux/Mac)

echo "================================================"
echo "Building Text File Merger Executable"
echo "================================================"
echo ""

# Check if PyInstaller is installed
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found. Installing..."
    pip3 install pyinstaller
    echo ""
fi

echo "Building executable..."
echo ""

# Build the executable
pyinstaller --onefile \
    --name "TextFileMerger" \
    --clean \
    text_file_merger.py

echo ""
echo "================================================"
echo "Build complete!"
echo "================================================"
echo ""
echo "The executable can be found at: dist/TextFileMerger"
echo ""
echo "You can now run: ./dist/TextFileMerger"
echo ""
echo "Note: config.json will be created in the same folder"
echo "      as the executable when you first run it."
echo ""
