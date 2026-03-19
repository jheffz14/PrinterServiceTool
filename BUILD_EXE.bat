@echo off
echo ============================================
echo   Printer Service Tool - Build EXE
echo ============================================
echo.

echo Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.8+ first.
    pause
    exit /b
)

echo.
echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist"  rmdir /s /q dist

echo.
echo Building EXE...
pyinstaller build.spec --clean

echo.
echo ============================================
if exist "dist\PrinterServiceTool\PrinterServiceTool.exe" (
    echo   SUCCESS!
    echo.
    echo   Your EXE folder is at:
    echo   dist\PrinterServiceTool\
    echo.
    echo   Copy the ENTIRE "PrinterServiceTool" folder
    echo   to any other Windows computer and run
    echo   PrinterServiceTool.exe inside it.
    echo.
    echo   No Python needed on the other computer!
) else (
    echo   BUILD FAILED - check errors above
)
echo ============================================
pause
