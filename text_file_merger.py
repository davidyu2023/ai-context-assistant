"""
Text File Merger - GUI Application
Combines multiple text files from selected folders into single output files
with clear delimiters and timestamps.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


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
            "file_extensions": ".txt, .py, .md, .json, .xml, .csv"
        }

    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.data.get(key, default)

    def set(self, key: str, value):
        """Set configuration value and save"""
        self.data[key] = value
        self.save()


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
                       variable=self.include_subfolders).pack(side=tk.LEFT)

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
            "output_name": self.output_name.get()
        }


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

    def setup_gui(self):
        """Setup the GUI components"""

        # Main container with scrollbar
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Settings Section
        settings_frame = ttk.LabelFrame(main_container, text="Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Output folder
        output_folder_frame = ttk.Frame(settings_frame)
        output_folder_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(output_folder_frame, text="Output Folder:").pack(side=tk.LEFT)
        self.output_folder = tk.StringVar(value=self.config.get("output_folder", ""))
        ttk.Entry(output_folder_frame, textvariable=self.output_folder,
                 width=50, state='readonly').pack(side=tk.LEFT, padx=5, fill=tk.X,
                                                  expand=True)
        ttk.Button(output_folder_frame, text="Browse...",
                  command=self.browse_output_folder).pack(side=tk.LEFT)

        # File extensions
        extensions_frame = ttk.Frame(settings_frame)
        extensions_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(extensions_frame, text="File Extensions:").pack(side=tk.LEFT)
        self.file_extensions = tk.StringVar(
            value=self.config.get("file_extensions", ".txt, .py, .md"))
        ttk.Entry(extensions_frame, textvariable=self.file_extensions,
                 width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(extensions_frame,
                 text="(comma-separated, e.g., .txt, .py, .md)").pack(side=tk.LEFT)

        # Save settings button
        ttk.Button(settings_frame, text="Save Settings",
                  command=self.save_settings).pack(pady=(5, 0))

        # Source Folders Section
        folders_container = ttk.LabelFrame(main_container, text="Source Folders",
                                          padding="10")
        folders_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Canvas with scrollbar for folder entries
        canvas_frame = ttk.Frame(folders_container)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, height=300)
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
        button_frame = ttk.Frame(folders_container)
        button_frame.pack(fill=tk.X, pady=(5, 0))

        self.add_folder_btn = ttk.Button(button_frame, text="Add Folder",
                                         command=self.add_folder_entry)
        self.add_folder_btn.pack(side=tk.LEFT)

        self.folder_count_label = ttk.Label(button_frame,
                                           text=f"Folders: 0/{self.MAX_FOLDERS}")
        self.folder_count_label.pack(side=tk.LEFT, padx=10)

        # Action Buttons
        action_frame = ttk.Frame(main_container)
        action_frame.pack(fill=tk.X)

        ttk.Button(action_frame, text="Generate Output Files",
                  command=self.generate_outputs,
                  style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Clear All Folders",
                  command=self.clear_all_folders).pack(side=tk.LEFT)

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
        self.log("Settings saved successfully")
        messagebox.showinfo("Settings", "Settings saved successfully!")

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

    def collect_files(self, folder_path: str, exclude_subfolders: bool,
                     extensions: List[str]) -> List[Path]:
        """Collect all files from folder matching extensions"""
        files = []
        folder = Path(folder_path)

        if exclude_subfolders:
            # Only get files in the root folder
            for file_path in folder.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in extensions:
                    files.append(file_path)
        else:
            # Recursively get all files
            for ext in extensions:
                files.extend(folder.rglob(f"*{ext}"))

        return sorted(files)

    def merge_files(self, files: List[Path], output_path: str) -> bool:
        """Merge multiple files into one with delimiters"""
        try:
            with open(output_path, 'w', encoding='utf-8', errors='ignore') as outfile:
                outfile.write(f"Generated by AI Context Assistant\n")
                outfile.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                outfile.write(f"Total files: {len(files)}\n")
                outfile.write("\n" + "="*80 + "\n\n")

                for file_path in files:
                    try:
                        # Write file header
                        outfile.write("="*80 + "\n")
                        outfile.write(f"BEGIN FILE: {file_path}\n")
                        outfile.write("="*80 + "\n")

                        # Write file content
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                            content = infile.read()
                            outfile.write(content)
                            # Ensure file ends with newline
                            if content and not content.endswith('\n'):
                                outfile.write('\n')

                        # Write file footer
                        outfile.write("="*80 + "\n")
                        outfile.write(f"END FILE: {file_path}\n")
                        outfile.write("="*80 + "\n\n")

                    except Exception as e:
                        self.log(f"Error reading {file_path}: {e}")
                        continue

            return True
        except Exception as e:
            self.log(f"Error writing output file: {e}")
            return False

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

        # Process each folder
        for i, config in enumerate(folder_configs, 1):
            folder_path = config['folder_path']
            exclude_subfolders = config['exclude_subfolders']
            output_name = config['output_name']

            self.log(f"\n[{i}/{len(folder_configs)}] Processing: {folder_path}")
            self.log(f"  Exclude subfolders: {exclude_subfolders}")

            # Collect files
            files = self.collect_files(folder_path, exclude_subfolders, extensions)

            if not files:
                self.log(f"  Warning: No matching files found")
                continue

            self.log(f"  Found {len(files)} file(s)")

            # Generate output filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{output_name}_{timestamp}.txt"
            output_path = os.path.join(self.output_folder.get(), output_filename)

            # Merge files
            if self.merge_files(files, output_path):
                self.log(f"  Success: Created {output_filename}")
                success_count += 1
            else:
                self.log(f"  Error: Failed to create output file")

        self.log("="*60)
        self.log(f"Process complete: {success_count}/{len(folder_configs)} successful")
        self.log("="*60)

        messagebox.showinfo("Complete",
                          f"Generated {success_count} output file(s)\n"
                          f"Location: {self.output_folder.get()}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = TextFileMergerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
