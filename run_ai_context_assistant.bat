@echo off
REM AI Context Assistant Launcher
REM Pin this file to your Windows taskbar for easy access

REM Get the directory where this batch file is located
cd /d "%~dp0"

REM Check if virtual environment exists and activate it
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Launch the AI Context Assistant
echo Starting AI Context Assistant...
python text_file_merger.py

REM If there was an error, pause so user can see the error message
if errorlevel 1 (
    echo.
    echo ERROR: Failed to start AI Context Assistant
    echo Make sure Python is installed and dependencies are installed.
    echo.
    pause
)
