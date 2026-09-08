# -*- coding: utf-8 -*-
"""
配置文件。

本程序的所有可调参数都集中在这里。图形界面里的“设置”窗口修改后会
保存到用户数据目录下的 config.json，下次启动自动读取，无需手动编辑本文件。

存放位置：%APPDATA%/VoiceAssistant/config.json
"""
import json
import os

APP_NAME = "VoiceAssistant"
APP_VERSION = "1.0.0"

# 默认系统提示词（告诉 AI 它是什么）
DEFAULT_SYSTEM_PROMPT = (
    "你的名字是贾维斯（JARVIS），是用户专属的 AI 语音助手。"
    "无论底层模型是什么，你都必须自称“贾维斯”，不要透露其他模型或厂商身份。"
    "请用中文简明扼要地回答用户的问题，回答要友好、可靠、简洁。"
)

# 各项参数的默认值（首次运行 / 配置文件缺失时使用）
DEFAULTS = {
    # ---------- AI 模型 ----------
    # model_type 可选：agnes / ollama / lm_studio / openai / siliconflow / deepseek / custom
    "model_type": "agnes",
    # 注意：源码默认不含 API Key（私人数据仅保存在本机 %APPDATA%/VoiceAssistant/config.json）
    "api_key": "",
    "base_url": "https://apihub.agnes-ai.com/v1",
    "model_name": "agnes-3.0-flash",
    "temperature": 0.7,
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    # ---------- 语音识别 ----------
    # stt_engine 可选：offline（内置 vosk 离线识别，零联网）/ online（Google 在线识别，更准）
    "stt_engine": "offline",
    "language": "zh-CN",
    # 麦克风设备索引：-1 表示系统默认麦克风；可在“设置”中随意切换
    "mic_device": -1,
    # ---------- 语音播报 ----------
    # tts_engine 可选：local（Windows 本地合成，完全离线）/ edge（微软在线合成，音质更好）
    "tts_engine": "local",
    "tts_voice": "zh-CN-XiaoxiaoNeural",
    # ---------- 唤醒与热键 ----------
    "wake_enabled": True,
    "wake_word": "嗨,贾维斯",
    "hotkey": "ctrl+alt+space",
    "always_on_top": True,
}

# 各模型类型的默认参数（设置窗口选中后自动填充，仍可手动修改）
MODEL_PRESETS = {
    "agnes": {"base_url": "https://apihub.agnes-ai.com/v1", "model_name": "agnes-3.0-flash"},
    "ollama": {"base_url": "http://localhost:11434/v1", "model_name": "qwen2.5:7b"},
    "lm_studio": {"base_url": "http://localhost:1234/v1", "model_name": "local-model"},
    "openai": {"base_url": "https://api.openai.com/v1", "model_name": "gpt-4o-mini"},
    "siliconflow": {"base_url": "https://api.siliconflow.cn/v1",
                    "model_name": "Qwen/Qwen2.5-7B-Instruct"},
    "deepseek": {"base_url": "https://api.deepseek.com/v1", "model_name": "deepseek-chat"},
    "custom": {"base_url": "", "model_name": ""},
}

MODEL_TYPE_LABELS = {
    "agnes": "云端模型 · APIHub（agnes）",
    "ollama": "本地模型 · Ollama（本机运行）",
    "lm_studio": "本地模型 · LM Studio（本机运行）",
    "openai": "云端模型 · OpenAI",
    "siliconflow": "云端模型 · 硅基流动 SiliconFlow",
    "deepseek": "云端模型 · DeepSeek",
    "custom": "自定义 · 任意 OpenAI 兼容接口",
}


def app_data_dir():
    """用户数据目录：日志、离线模型缓存等存放处。"""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, APP_NAME)
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        pass
    return folder


def _config_path():
    return os.path.join(app_data_dir(), "config.json")


def load_config():
    """读取配置；文件缺失或损坏时返回默认值，绝不抛异常。"""
    cfg = dict(DEFAULTS)
    path = _config_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k in DEFAULTS:
                    if k in data and data[k] is not None:
                        cfg[k] = data[k]
    except Exception:
        pass
    return cfg


def save_config(cfg):
    """保存配置到用户数据目录。失败时静默返回 False，不阻塞主程序。"""
    try:
        path = _config_path()
        data = {k: cfg.get(k) for k in DEFAULTS}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
