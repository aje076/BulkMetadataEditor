@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.11+ is required. Install it from python.org and enable Add Python to PATH.
  pause
  exit /b 1
)
if not exist "exiftool\exiftool.exe" (
  echo Missing exiftool\exiftool.exe and exiftool\exiftool_files.
  echo See README.txt for download and setup instructions.
  pause
  exit /b 1
)
python -m pip install --upgrade pip
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --name BulkMetadataEditor --onedir --add-data "exiftool;exiftool" bulk_metadata_editor.py
if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)
echo.
echo Build complete: dist\BulkMetadataEditor\BulkMetadataEditor.exe
 echo Now open installer\BulkMetadataEditor.iss in Inno Setup 6 and click Compile to create Setup.exe
pause
