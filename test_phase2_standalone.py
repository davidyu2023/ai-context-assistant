#!/usr/bin/env python3
"""
Standalone test for Phase 2 utility functions (no tkinter dependency)
"""

import ast
from pathlib import Path
from typing import List, Dict, Optional

# ========== Skeleton Extraction ==========
def extract_skeleton(file_path: Path) -> Optional[str]:
    """Extract code skeleton from Python files"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        skeleton_lines = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_line = f"class {node.name}"
                if node.bases:
                    bases = ', '.join(ast.unparse(base) for base in node.bases)
                    class_line += f"({bases})"
                class_line += ":"
                skeleton_lines.append(class_line)

                if (ast.get_docstring(node)):
                    docstring = ast.get_docstring(node)
                    skeleton_lines.append(f'    """{docstring}"""')

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
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

                        if ast.get_docstring(item):
                            docstring = ast.get_docstring(item)
                            skeleton_lines.append(f'        """{docstring}"""')

                        skeleton_lines.append("        ...")
                        skeleton_lines.append("")

                skeleton_lines.append("")

        return '\n'.join(skeleton_lines) if skeleton_lines else None

    except Exception:
        return None

# ========== Directory Tree ==========
def generate_directory_tree(folder_path: Path, files: List[Path]) -> str:
    """Generate text-based directory tree"""
    structure = {}
    for file in files:
        try:
            relative = file.relative_to(folder_path)
            parts = relative.parts

            current = structure
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    if 'files' not in current:
                        current['files'] = []
                    current['files'].append(part)
                else:
                    if 'dirs' not in current:
                        current['dirs'] = {}
                    if part not in current['dirs']:
                        current['dirs'][part] = {}
                    current = current['dirs'][part]
        except ValueError:
            continue

    def build_tree(node: Dict, prefix: str = "") -> List[str]:
        lines = []
        if 'dirs' in node:
            dirs = sorted(node['dirs'].items())
            for i, (dir_name, sub_node) in enumerate(dirs):
                is_last_dir = (i == len(dirs) - 1) and 'files' not in node
                connector = "└── " if is_last_dir else "├── "
                lines.append(f"{prefix}{connector}{dir_name}/")
                extension = "    " if is_last_dir else "│   "
                lines.extend(build_tree(sub_node, prefix + extension))

        if 'files' in node:
            files_list = sorted(node['files'])
            for i, file_name in enumerate(files_list):
                is_last_file = i == len(files_list) - 1
                connector = "└── " if is_last_file else "├── "
                lines.append(f"{prefix}{connector}{file_name}")

        return lines

    tree_lines = [f"{folder_path.name}/"]
    tree_lines.extend(build_tree(structure))
    return '\n'.join(tree_lines)

# ========== Tests ==========
def test_skeleton():
    print("=" * 60)
    print("SKELETON MODE TEST")
    print("=" * 60)

    test_file = Path(__file__)
    skeleton = extract_skeleton(test_file)

    if skeleton:
        orig_len = len(test_file.read_text())
        skel_len = len(skeleton)
        reduction = (1 - skel_len / orig_len) * 100

        print(f"✓ Skeleton extraction successful")
        print(f"  Original: {orig_len} chars")
        print(f"  Skeleton: {skel_len} chars")
        print(f"  Reduction: {reduction:.1f}%")
        print()
        print("Sample output (first 200 chars):")
        print(skeleton[:200])
    else:
        print("✗ Skeleton extraction failed")

    print()

def test_directory_tree():
    print("=" * 60)
    print("DIRECTORY TREE TEST")
    print("=" * 60)

    test_dir = Path(__file__).parent
    test_files = list(test_dir.glob("*.py"))[:3]

    tree = generate_directory_tree(test_dir, test_files)

    print("Generated tree:")
    print(tree)
    print(f"\n✓ Tree generation successful ({len(test_files)} files)")
    print()

def main():
    print("\n" + "=" * 60)
    print("PHASE 2 UTILITY FUNCTIONS TEST")
    print("=" * 60)
    print()

    test_skeleton()
    test_directory_tree()

    print("=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()
