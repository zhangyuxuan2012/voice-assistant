@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title VoiceAssistant Launcher

if exist "VoiceAssistant.exe" (
    start "" "VoiceAssistant.exe"
    exit /b 0
)

echo.
echo 未找到 VoiceAssistant.exe。
echo 请先运行 build_exe.bat 打包，或下载已打包好的发布版本。
echo.
pause
exit /b 1
