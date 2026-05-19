@echo off
:: Request Administrator privileges
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "cmd.exe", "/c %~s0", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%~dp0"

    :: --- Dependency Check ---
    echo Checking environment...

    :: 1. Check if Python is installed
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python is not installed or not in PATH.
        echo Please install Python from python.org and try again.
        pause
        exit /B
    )

    :: 2. Ensure pip is up to date
    echo Updating pip...
    python -m pip install --upgrade pip --quiet

    :: 3. Install requirements from requirements.txt
    :: This command checks and installs PyQt6, pynput, and pywin32 
    if exist "requirements.txt" (
        echo Checking/Installing dependencies from requirements.txt...
        python -m pip install -r requirements.txt --quiet
    ) else (
        echo [WARNING] requirements.txt not found. Skipping dependency install.
    )

    :: --- Launch Program ---
    echo Starting Obsidian Macro Client...
    :: Launches the main script as requested 
    python main.py
    
    if %errorlevel% neq 0 (
        echo [ERROR] The application crashed or failed to start.
        pause
    )