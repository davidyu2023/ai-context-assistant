#!/usr/bin/env python3
"""
Sync from Google Drive - Download Google Docs as Markdown

Downloads Google Docs from Google Drive and converts them to Markdown files
for local use. Designed for pulling Gemini-generated docs.

DEFAULT USAGE (download ALL docs from Drive root):
    python sync_from_drive.py                         # Downloads all to _active
    python sync_from_drive.py --list                  # List docs (dry run)
    python sync_from_drive.py --gem calc-core         # Downloads all to specific gem

SPECIFIC DOC:
    python sync_from_drive.py "My Document Name"      # Saves to _active (default)
    python sync_from_drive.py "design doc" --gem X    # Saves to specific gem

FILES ARE SAVED WITH PREFIX: temp_from_gem_
    Example: _source/_active/refs/temp_from_gem_my-document-name.md

CLEANUP (when ready to remove integrated files):
    python sync_from_drive.py --cleanup                # List all temp files
    python sync_from_drive.py --cleanup --confirm      # Delete all temp files

Prerequisites:
    1. credentials.json in this folder (from Google Cloud Console)
    2. pip install google-auth-oauthlib google-api-python-client
    3. First run: authenticate via browser (creates token.json)

Workflow:
    1. Gemini creates Google Doc(s) in Drive root
    2. Run: python sync_from_drive.py (downloads all to _active)
    3. Review, discuss, integrate content when ready
    4. Delete temp files or move to target gem folder
    5. Keep Drive root folder clean
"""

import os
import sys
import argparse
import re
from pathlib import Path
from datetime import datetime

# Check for required packages
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Required packages not installed. Run:")
    print("  pip install google-auth-oauthlib google-api-python-client")
    sys.exit(1)

# Configuration
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent  # mtl/
GEMINI_SOURCE = REPO_ROOT / "docs" / "DocsShell" / "Context" / "ai-contexts" / "gemini" / "_source"
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"

# Prefix for temporary Gemini imports
TEMP_PREFIX = "temp_from_gem_"

# Scopes - need readonly to access docs created by other apps (like Gemini)
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Export mime types to try (in order of preference)
EXPORT_MIME_TYPES = [
    ('text/markdown', '.md'),      # Native markdown (added 2024)
    ('text/plain', '.txt'),        # Fallback to plain text
]

# Known gem shortcuts and their folder names
GEM_SHORTCUTS = {
    # Webapp gems
    'inmodel-domain': 'web-inmodel-domain',
    'inmodel-app': 'web-inmodel-application',
    'inmodel-infra': 'web-inmodel-infrastructure',
    'finmodels-domain': 'web-finmodels-domain',
    'finmodels-app': 'web-finmodels-application',
    # Calc service gems
    'contracts': 'calc-contracts',
    'calc-core': 'calc-core',
    'calc-app': 'calc-application',
    'calc-common': 'calc-common',
    'calc-data': 'calc-data',
    'calc-tables': 'calc-tables',
    'calc-workers': 'calc-workers',
    'calc-projworkers': 'calc-projworkers',
    'calc-trackrecs': 'calc-trackrecs',
    'calc-meshes': 'calc-meshes',
    'calc-infra': 'calc-infrastructure',
    # Special
    'active': '_active',
    'shared': '_shared',
}


def resolve_gem_folder(gem_name):
    """
    Resolve a gem name/shortcut to the full folder path.

    Args:
        gem_name: Gem name or shortcut (e.g., 'calc-core', 'inmodel-domain')

    Returns:
        Path to the gem's refs folder, or None if not found
    """
    # Check if it's a shortcut
    folder_name = GEM_SHORTCUTS.get(gem_name, gem_name)

    # Build path to refs folder
    gem_path = GEMINI_SOURCE / folder_name / "refs"

    # Also check without 'refs' in case they want a different subfolder
    if not gem_path.parent.exists():
        # Try direct path
        alt_path = GEMINI_SOURCE / folder_name
        if alt_path.exists():
            return alt_path / "refs"

    return gem_path


def authenticate():
    """Authenticate with Google Drive API."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed: {e}")
                print("Deleting old token and re-authenticating...")
                TOKEN_FILE.unlink(missing_ok=True)
                creds = None

        if not creds:
            if not CREDENTIALS_FILE.exists():
                print(f"Error: credentials.json not found at {CREDENTIALS_FILE}")
                print("\nTo set up credentials:")
                print("1. Go to Google Cloud Console")
                print("2. Create OAuth Client ID (Desktop app)")
                print("3. Download JSON and save as 'credentials.json' in this folder")
                sys.exit(1)

            print("Opening browser for authentication...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print(f"Token saved to {TOKEN_FILE}")

    return build('drive', 'v3', credentials=creds)


def find_folder(service, folder_name):
    """Find a folder by name in Google Drive."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])

    if files:
        if len(files) > 1:
            print(f"Warning: Multiple folders named '{folder_name}' found. Using first match.")
        return files[0]['id']
    return None


def search_doc_by_name(service, doc_name, folder_id=None):
    """
    Search for a Google Doc by name.

    Args:
        service: Google Drive API service
        doc_name: Name (or partial name) of document to find
        folder_id: Optional folder ID to search in (None = root)

    Returns:
        List of matching docs with 'id', 'name', 'modifiedTime'
    """
    query_parts = [
        f"name contains '{doc_name}'",
        "mimeType='application/vnd.google-apps.document'",
        "trashed=false"
    ]

    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")
    else:
        query_parts.append("'root' in parents")

    query = " and ".join(query_parts)

    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, modifiedTime, createdTime)',
        orderBy='modifiedTime desc'
    ).execute()

    return results.get('files', [])


def list_google_docs(service, folder_id=None):
    """List all Google Docs in a folder or root."""
    if folder_id:
        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"
    else:
        query = "'root' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"

    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, modifiedTime, createdTime)',
        orderBy='modifiedTime desc'
    ).execute()

    return results.get('files', [])


def sanitize_filename(name):
    """Convert a document name to a valid filename."""
    name = name.lower()
    name = re.sub(r'[\s_]+', '-', name)
    name = re.sub(r'[^a-z0-9\-]', '', name)
    name = re.sub(r'-+', '-', name)
    name = name.strip('-')
    return name if name else 'untitled'


def export_google_doc(service, file_id, file_name, target_folder, add_prefix=True):
    """
    Export a Google Doc to Markdown file.

    Args:
        service: Google Drive API service
        file_id: ID of the Google Doc
        file_name: Original name of the document
        target_folder: Path to save the exported file
        add_prefix: Whether to add temp_from_gem_ prefix

    Returns:
        Tuple of (success: bool, local_path: Path or None, message: str)
    """
    target_folder = Path(target_folder)
    target_folder.mkdir(parents=True, exist_ok=True)

    sanitized_name = sanitize_filename(file_name)
    if add_prefix:
        sanitized_name = f"{TEMP_PREFIX}{sanitized_name}"

    for mime_type, extension in EXPORT_MIME_TYPES:
        try:
            content = service.files().export(
                fileId=file_id,
                mimeType=mime_type
            ).execute()

            if isinstance(content, bytes):
                content = content.decode('utf-8')

            local_path = target_folder / f"{sanitized_name}{extension}"
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True, local_path, f"Exported as {extension}"

        except HttpError as e:
            if e.resp.status == 403 and 'exportFormat' in str(e):
                continue
            raise

    return False, None, "No supported export format available"


def get_doc_by_name(service, doc_name, target_folder):
    """
    Quick function to grab a specific doc by name from root folder.

    Returns:
        Path to downloaded file, or None if not found
    """
    print(f"Searching for '{doc_name}' in Google Drive root...")

    docs = search_doc_by_name(service, doc_name, folder_id=None)

    if not docs:
        print(f"No document matching '{doc_name}' found in root folder.")
        return None

    if len(docs) > 1:
        print(f"Found {len(docs)} matching documents:")
        for i, doc in enumerate(docs, 1):
            modified = doc.get('modifiedTime', 'Unknown')[:10]
            print(f"  {i}. {doc['name']} (modified: {modified})")
        print(f"\nDownloading first match: {docs[0]['name']}")

    doc = docs[0]
    success, local_path, message = export_google_doc(service, doc['id'], doc['name'], target_folder)

    if success:
        print(f"\n[OK] Downloaded: {doc['name']}")
        print(f"     Saved to: {local_path}")
        print(f"\n     Prefix '{TEMP_PREFIX}' indicates this is a Gemini import.")
        print(f"     Rename or delete after integration.")
        return local_path
    else:
        print(f"\n[ERROR] Failed to download: {message}")
        return None


def download_docs(service, folder_id, folder_name, target_folder, specific_file=None, dry_run=False):
    """Download Google Docs from a folder to local markdown files."""
    docs = list_google_docs(service, folder_id)

    if not docs:
        location = f"folder '{folder_name}'" if folder_name else "root folder"
        print(f"No Google Docs found in {location}")
        return 0

    if specific_file:
        specific_lower = specific_file.lower()
        docs = [d for d in docs if specific_lower in d['name'].lower()]
        if not docs:
            print(f"No document matching '{specific_file}' found")
            return 0

    if dry_run:
        location = f"'{folder_name}'" if folder_name else "root"
        print(f"\nGoogle Docs in {location} ({len(docs)}):")
        print("-" * 60)
        for doc in docs:
            modified = doc.get('modifiedTime', 'Unknown')[:10]
            print(f"  {doc['name']}")
            print(f"    Modified: {modified}")
        print("-" * 60)
        print(f"\nWould download to: {target_folder}")
        return len(docs)

    print(f"\nDownloading {len(docs)} document(s)")
    print(f"Target: {target_folder}")
    print("-" * 60)

    downloaded = 0
    for doc in docs:
        try:
            success, local_path, message = export_google_doc(
                service, doc['id'], doc['name'], target_folder
            )
            if success:
                print(f"  [OK] {doc['name']} -> {local_path.name}")
                downloaded += 1
            else:
                print(f"  [SKIP] {doc['name']}: {message}")
        except HttpError as e:
            print(f"  [ERROR] {doc['name']}: {e}")
        except Exception as e:
            print(f"  [ERROR] {doc['name']}: {e}")

    print("-" * 60)
    print(f"Downloaded {downloaded}/{len(docs)} files")

    return downloaded


def list_all_folders(service, max_results=50):
    """List all folders in Google Drive."""
    query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        pageSize=max_results,
        orderBy='name'
    ).execute()

    return results.get('files', [])


def cleanup_temp_files(dry_run=True):
    """
    List or remove all temp_from_gem_* files across all gem folders.

    Args:
        dry_run: If True, only list files. If False, delete them.

    Returns:
        Number of files found/deleted
    """
    # Search all gem folders for temp files
    pattern = f"{TEMP_PREFIX}*.md"
    all_temp_files = list(GEMINI_SOURCE.rglob(pattern))

    # Also check for .txt files
    pattern_txt = f"{TEMP_PREFIX}*.txt"
    all_temp_files.extend(GEMINI_SOURCE.rglob(pattern_txt))

    if not all_temp_files:
        print("No temporary Gemini import files found.")
        return 0

    # Group by gem folder for display
    files_by_gem = {}
    for f in all_temp_files:
        # Get relative path from _source
        rel_path = f.relative_to(GEMINI_SOURCE)
        gem_name = rel_path.parts[0] if rel_path.parts else "unknown"
        if gem_name not in files_by_gem:
            files_by_gem[gem_name] = []
        files_by_gem[gem_name].append(f)

    print(f"\nTemporary Gemini imports ({TEMP_PREFIX}*):")
    print("=" * 60)

    total_size = 0
    for gem_name in sorted(files_by_gem.keys()):
        files = files_by_gem[gem_name]
        print(f"\n  {gem_name}/")
        for f in files:
            size_kb = f.stat().st_size / 1024
            total_size += size_kb
            modified = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d')
            # Show subfolder if not directly in gem root
            rel = f.relative_to(GEMINI_SOURCE / gem_name)
            print(f"    {rel} ({size_kb:.1f} KB, {modified})")

    print("=" * 60)
    print(f"Total: {len(all_temp_files)} file(s), {total_size:.1f} KB")

    if dry_run:
        print(f"\nTo delete these files, run:")
        print(f"  python sync_from_drive.py --cleanup --confirm")
    else:
        for f in all_temp_files:
            f.unlink()
        print(f"\nDeleted {len(all_temp_files)} file(s)")

    return len(all_temp_files)


def list_gems():
    """List available gem folders."""
    print("\nAvailable gems:")
    print("-" * 40)

    # List actual folders that exist
    existing = []
    for folder in GEMINI_SOURCE.iterdir():
        if folder.is_dir() and not folder.name.startswith('.'):
            existing.append(folder.name)

    for name in sorted(existing):
        # Check if it has a shortcut
        shortcuts = [k for k, v in GEM_SHORTCUTS.items() if v == name]
        if shortcuts:
            print(f"  {name} (shortcut: {shortcuts[0]})")
        else:
            print(f"  {name}")

    print("-" * 40)
    print(f"Total: {len(existing)} gems")


def main():
    parser = argparse.ArgumentParser(
        description='Download Google Docs from Drive as Markdown files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
DEFAULT (download ALL docs from Drive root to _active):
  python sync_from_drive.py                                    # Downloads all from root to _active
  python sync_from_drive.py --list                             # List docs in root (dry run)

SPECIFIC DOC (by name):
  python sync_from_drive.py "Document Name"                    # Saves to _active (default)
  python sync_from_drive.py "design doc" --gem calc-core       # Saves to specific gem

BULK TO SPECIFIC GEM:
  python sync_from_drive.py --gem calc-core                    # All root docs to calc-core

FILES ARE SAVED AS: temp_from_gem_<name>.md
  - Default location: _source/_active/refs/
  - With --gem: _source/<gem>/refs/
  - Prefix indicates Gemini import, awaiting integration

BROWSE:
  python sync_from_drive.py --list                # List docs in Drive root
  python sync_from_drive.py --list-gems           # List available gem folders

CLEANUP (periodic):
  python sync_from_drive.py --cleanup             # List all temp files
  python sync_from_drive.py --cleanup --confirm   # Delete all temp files

WORKFLOW:
  1. Gemini creates docs in Drive root
  2. Run: python sync_from_drive.py (downloads all to _active)
  3. Review/integrate content
  4. Delete temp files or move to specific gem
  5. Keep Drive root folder clean
"""
    )

    # Positional argument for quick doc name lookup
    parser.add_argument('doc_name', nargs='?',
                        help='Document name to download from root (quick mode)')

    # Gem target
    parser.add_argument('--gem', '-g',
                        help='Target gem folder (e.g., calc-core, inmodel-domain)')

    # Folder-based options
    parser.add_argument('--folder', '-f',
                        help='Google Drive folder name to download from')
    parser.add_argument('--root', '-r', action='store_true',
                        help='Search in root folder instead of a subfolder')
    parser.add_argument('--file',
                        help='Download specific document only (partial name match)')
    parser.add_argument('--target', '-t',
                        help='Custom target folder (overrides --gem)')

    # List/discovery options
    parser.add_argument('--list', '-l', action='store_true',
                        help='List documents without downloading (dry run)')
    parser.add_argument('--list-folders', action='store_true',
                        help='List available folders in Google Drive')
    parser.add_argument('--list-gems', action='store_true',
                        help='List available local gem folders')

    # Cleanup options
    parser.add_argument('--cleanup', '-c', action='store_true',
                        help='List/delete temporary Gemini import files')
    parser.add_argument('--confirm', action='store_true',
                        help='Confirm deletion when used with --cleanup')

    args = parser.parse_args()

    # Handle local-only operations first (no auth needed)
    if args.cleanup:
        return cleanup_temp_files(dry_run=not args.confirm)

    if args.list_gems:
        list_gems()
        return 0

    print("=" * 60)
    print("Google Drive to Markdown Sync")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Authenticate
    try:
        service = authenticate()
    except Exception as e:
        print(f"\nAuthentication failed: {e}")
        return 1

    # Quick mode: positional argument for doc name
    if args.doc_name:
        # Determine target folder (default to _active)
        if args.target:
            target = Path(args.target) if Path(args.target).is_absolute() else GEMINI_SOURCE / args.target
        elif args.gem:
            target = resolve_gem_folder(args.gem)
            print(f"Target gem: {args.gem} -> {target}")
        else:
            # Default to _active
            target = resolve_gem_folder('active')
            print(f"Target gem: _active (default) -> {target}")

        result = get_doc_by_name(service, args.doc_name, target)
        return 0 if result else 1

    # List folders mode
    if args.list_folders:
        print("\nFolders in Google Drive:")
        print("-" * 60)
        folders = list_all_folders(service)
        if folders:
            for folder in folders:
                print(f"  {folder['name']}")
        else:
            print("  (no folders found)")
        print("-" * 60)
        print(f"Total: {len(folders)} folders")
        return 0

    # Determine source (folder or root)
    folder_id = None
    folder_name = None

    if args.folder:
        folder_id = find_folder(service, args.folder)
        if not folder_id:
            print(f"\nError: Folder '{args.folder}' not found in Google Drive")
            print("Use --list-folders to see available folders")
            return 1
        folder_name = args.folder
    else:
        # Default to root folder (no need for --root flag anymore)
        folder_id = None
        folder_name = None

    # Resolve target folder (default to _active)
    if args.target:
        target_folder = Path(args.target) if Path(args.target).is_absolute() else GEMINI_SOURCE / args.target
    elif args.gem:
        target_folder = resolve_gem_folder(args.gem)
    else:
        # Default to _active for bulk downloads
        target_folder = resolve_gem_folder('active')

    location = f"folder '{folder_name}'" if folder_name else "root folder"
    print(f"Source: {location}")
    print(f"Target: {target_folder}")

    # Download documents
    try:
        downloaded = download_docs(
            service,
            folder_id,
            folder_name,
            target_folder,
            specific_file=args.file,
            dry_run=args.list
        )

        if not args.list and downloaded > 0:
            print(f"\nFiles saved to: {target_folder}")
            print(f"Files have prefix: {TEMP_PREFIX}")
            print("\nNext steps:")
            print("  1. Review the downloaded markdown file(s)")
            print("  2. Integrate content when ready")
            print("  3. Rename (remove prefix) or delete after integration")

    except HttpError as e:
        print(f"\nGoogle API Error: {e}")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
