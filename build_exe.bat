@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Build VoiceAssistant

echo [1/4] 检查 Python ...
python --version >nul 2>&1 || (
    echo 未检测到 Python，请先安装 Python 3.10+ 并加入 PATH。
    pause & exit /b 1
)

echo [2/4] 安装依赖 ...
python -m pip install -r requirements.txt || (
    echo 依赖安装失败。 & pause & exit /b 1
)

echo [3/4] 准备离线语音识别模型 ...
python tools\prepare_models.py || (
    echo 模型下载失败，可稍后重试。 & pause & exit /b 1
)

echo [3.5/4] 生成应用图标（如缺失）...
if not exist "voice_assistant.ico" (
    python make_icon.py
)

echo [4/4] 打包 EXE ...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name VoiceAssistant ^
    --icon voice_assistant.ico ^
    --version-file version_info.txt ^
    --add-data "models\vosk-model-small-cn-0.22;models\vosk-model-small-cn-0.22" ^
    --hidden-import pyttsx3.drivers ^
    --hidden-import pyttsx3.drivers.sapi5 ^
    --hidden-import win32com.client ^
    --collect-all vosk ^
    main.py

if exist "dist\VoiceAssistant.exe" (
    echo.
    echo 打包完成：dist\VoiceAssistant.exe
    echo 运行自检：dist\VoiceAssistant.exe --selftest
) else (
    echo 打包失败，请查看上方日志。
)
pause
exit /b 0
