"""
Script to create sample test data for the Text File Merger application
"""

import os
from pathlib import Path


def create_test_data():
    """Create sample folder structure with test files"""

    # Create test folders
    test_folders = [
        "test_data/project1",
        "test_data/project1/subfolder",
        "test_data/project2",
        "test_data/project2/docs",
        "test_data/output"
    ]

    for folder in test_folders:
        Path(folder).mkdir(parents=True, exist_ok=True)
        print(f"Created folder: {folder}")

    # Create sample files for project1
    files = {
        "test_data/project1/readme.txt": """# Project 1 README
This is a sample project for testing the Text File Merger application.
It contains multiple text files that will be merged together.
""",
        "test_data/project1/main.py": """# Main Python file
def hello_world():
    print("Hello from Project 1!")

if __name__ == "__main__":
    hello_world()
""",
        "test_data/project1/config.json": """{
    "name": "Project 1",
    "version": "1.0.0",
    "description": "Sample project configuration"
}
""",
        "test_data/project1/subfolder/notes.txt": """Notes for subfolder
This file is in a subfolder and will only be included if subfolders are not excluded.
""",
        "test_data/project1/subfolder/utils.py": """# Utility functions
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""",
        # Project 2 files
        "test_data/project2/info.txt": """Project 2 Information
This is another sample project for testing.
""",
        "test_data/project2/script.py": """# Script file
print("Hello from Project 2!")
""",
        "test_data/project2/data.csv": """name,age,city
Alice,30,New York
Bob,25,London
Charlie,35,Paris
""",
        "test_data/project2/docs/manual.md": """# User Manual

This is a sample markdown file in the docs subfolder.

## Features
- Feature 1
- Feature 2
- Feature 3
""",
    }

    # Write all files
    for filepath, content in files.items():
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Created file: {filepath}")

    print("\n" + "="*60)
    print("Test data created successfully!")
    print("="*60)
    print("\nTest folders:")
    print("  - test_data/project1 (has subfolder)")
    print("  - test_data/project2 (has docs subfolder)")
    print("  - test_data/output (for merged files)")
    print("\nFile types created:")
    print("  - .txt files")
    print("  - .py files")
    print("  - .json files")
    print("  - .csv files")
    print("  - .md files")
    print("\nYou can now test the application with these folders!")


if __name__ == "__main__":
    create_test_data()
