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
    echo [2/3] Build successful!
    echo [3/3] Copying portable Tesseract OCR...
    if exist "tesseract" (
        robocopy "tesseract" "dist\tesseract" /E /NFL /NDL /NJH /NJS /nc /ns /np 2>nul
        echo.
    ) else (
        echo   WARNING: tesseract/ folder not found - OCR will need manual setup
        echo   Run: python setup_tesseract.py
        echo.
    )
    echo ========================================
    echo   Build Complete!
    echo ========================================
    echo.
    echo Output folder: dist\
    echo   - TravelPlanner.exe  (20MB, standalone app)
    if exist "dist\tesseract" echo   - tesseract/         (portable OCR, Chinese+English)
    echo.
    echo To deploy to another computer:
    echo   1. Copy the entire "dist" folder
    echo   2. Double-click TravelPlanner.exe
    echo   3. OCR works out of the box - no installation needed!
    echo.
) else (
    echo [2/2] Build failed. Check errors above.
)

pause
