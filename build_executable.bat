@echo off
REM Build script for creating Windows executable

echo ================================================
echo Building Text File Merger Executable
echo ================================================
echo.

REM Check if PyInstaller is installed
py -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    py -m pip install pyinstaller
    echo.
)

echo Building executable...
echo.

REM Build the executable
py -m PyInstaller --onefile ^
    --windowed ^
    --name "TextFileMerger" ^
    --icon=NONE ^
    --clean ^
    text_file_merger.py

echo.
echo ================================================
echo Build complete!
echo ================================================
echo.
echo The executable can be found at: dist\TextFileMerger.exe
echo.
echo You can now:
echo   1. Run dist\TextFileMerger.exe directly
echo   2. Copy dist\TextFileMerger.exe to any location
echo   3. Create a desktop shortcut to the executable
echo.
echo Note: config.json will be created in the same folder
echo       as the executable when you first run it.
echo.
pause
