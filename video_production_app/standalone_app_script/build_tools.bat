@echo off
echo ========================================
echo Video Production App v3.0 - Build Tools
echo ========================================
echo.
echo Choose an option:
echo 1. Create standalone Python file
echo 2. Build executable (.exe) file
echo 3. Create logo for the app
echo 4. Run the app directly
echo 5. Exit
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" (
    echo.
    echo Creating standalone Python file...
    python create_standalone.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo Building executable file...
    python build_app.py
    pause
) else if "%choice%"=="3" (
    echo.
    echo Creating logo for the app...
    python create_logo.py
    pause
) else if "%choice%"=="4" (
    echo.
    echo Starting Video Production App...
    python video_production_app\main.py
    pause
) else if "%choice%"=="5" (
    echo Goodbye!
    exit
) else (
    echo Invalid choice. Please try again.
    pause
    goto :eof
)
