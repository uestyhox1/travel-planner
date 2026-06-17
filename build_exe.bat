@echo off
chcp 65001 >nul
echo ========================================
echo   Travel Planner - Build Tool
echo ========================================
echo.

:: Clean old builds
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul

echo [1/2] Building exe... (this may take 2-3 minutes)

pyinstaller --onefile ^
    --name "TravelPlanner" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --hidden-import flask ^
    --hidden-import flask_cors ^
    --hidden-import database ^
    --hidden-import ocr_engine ^
    --hidden-import parser ^
    --hidden-import xiaohongshu ^
    --hidden-import werkzeug ^
    --hidden-import jinja2 ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageEnhance ^
    --hidden-import PIL.ImageFilter ^
    --exclude-module torch ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module numpy ^
    --exclude-module lxml ^
    --exclude-module openpyxl ^
    --exclude-module tensorflow ^
    --exclude-module cv2 ^
    --exclude-module matplotlib ^
    --exclude-module easyocr ^
    --clean ^
    app.py

echo.
if exist "dist\TravelPlanner.exe" (
    echo [2/2] Build successful!
    echo.
    echo Output: dist\TravelPlanner.exe (15MB)
    echo ========================================
    echo.
    echo To use:
    echo   1. Double-click TravelPlanner.exe
    echo   2. Browser will open automatically
    echo   3. Upload travel guide images or paste text
    echo.
    echo Note: Place TravelPlanner.exe anywhere,
    echo       data will be stored alongside it.
) else (
    echo [2/2] Build failed. Check errors above.
)

pause
