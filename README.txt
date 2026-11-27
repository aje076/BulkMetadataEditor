# Bulk Metadata Editor — Windows 11 installer build

This project includes a Windows desktop metadata editor and an automated workflow that creates a proper Windows installer named `BulkMetadataEditor-Setup.exe`.

## Build the installer (no Python setup on your PC required)
1. Create a free GitHub account if you do not already have one.
2. Create a new repository and upload the contents of this ZIP (keep the `.github` folder).
3. Open the repository's **Actions** tab.
4. Select **Build Windows Setup.exe** and click **Run workflow**.
5. Wait for the Windows build to finish successfully.
6. Open the completed workflow run. Under **Artifacts**, download `BulkMetadataEditor-Setup`.
7. Extract the downloaded artifact ZIP. It contains `BulkMetadataEditor-Setup.exe`.
8. Run `BulkMetadataEditor-Setup.exe` on Windows 11 and follow the installer.

The workflow downloads ExifTool from its official website, bundles the application and ExifTool, and compiles the installer using Inno Setup. The installed program does not require Python to be installed separately.

## Build locally instead
1. Install Python 3.11+ and Inno Setup 6 on Windows.
2. Download the Windows executable distribution of ExifTool from https://exiftool.org/.
3. Place `exiftool.exe` and its `exiftool_files` support folder in an `exiftool` folder beside `bulk_metadata_editor.py`.
4. Run `build_windows.bat` to create `dist\\BulkMetadataEditor`.
5. Open `installer\\BulkMetadataEditor.iss` in Inno Setup Compiler and click Compile.
6. The installer is written to `release\\BulkMetadataEditor-Setup.exe`.

## Included functionality
- Select files or recursively add a folder.
- Read metadata and export the read data to CSV.
- Bulk-write filled XMP fields to one or more selected files. Blank fields are left unchanged.
- Show per-file write results, failure reasons, and suggested fixes; verify written values by reading them back.
- Rename selected files.
- Back up originals by default using ExifTool's `_original` files.

## Important limitations
Metadata tags differ by format. This app writes the configured XMP tags where the file format supports them; unsupported tags are reported for the affected file. A field appearing in the editor does not guarantee every file type supports it. Only files selected in the file list are changed; Ctrl/Shift-click selects multiple files. Blank fields are not sent to ExifTool and leave existing metadata unchanged. Backups are enabled by default. The Windows account running the app must have write access to each file.
