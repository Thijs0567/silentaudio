@echo off
REM Build silentaudio.exe (no console window) into dist\silentaudio.exe
python -m pip install --upgrade pip pyinstaller -r requirements.txt || goto :err
python -m PyInstaller --clean --noconfirm silentaudio.spec || goto :err
echo.
echo Built: %~dp0dist\silentaudio.exe
exit /b 0
:err
echo Build failed.
exit /b 1
