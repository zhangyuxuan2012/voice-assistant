# -*- coding: utf-8 -*-
"""自检：验证依赖、离线模型、麦克风是否就绪。

GUI 版（--windowed）没有控制台，结果同时写入：
  %APPDATA%/VoiceAssistant/selftest.txt
"""
import importlib
import os

import config
from core import audio, paths

_MODULES = [
    "PyQt6.QtWidgets", "sounddevice", "numpy", "speech_recognition",
    "openai", "keyboard", "edge_tts", "pyttsx3", "vosk",
    "core.audio", "core.llm", "core.tts", "core.hotkey", "core.wake",
]


def _report(lines):
    text = "\n".join(lines)
    try:
        print(text)
    except Exception:
        pass
    try:
        with open(os.path.join(config.app_data_dir(), "selftest.txt"),
                  "w", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass


def run_selftest():
    lines = ["=== VoiceAssistant 自检 ==="]
    failed = False

    try:
        cfg = config.load_config()
        lines.append(f"[OK] 配置加载：model={cfg['model_type']} "
                     f"stt={cfg['stt_engine']} tts={cfg['tts_engine']}")
    except Exception as e:
        failed = True
        lines.append(f"[FAIL] 配置加载：{e}")

    for m in _MODULES:
        try:
            importlib.import_module(m)
            lines.append(f"[OK] 导入 {m}")
        except Exception as e:
            failed = True
            lines.append(f"[FAIL] 导入 {m}: {e}")

    mp = paths.vosk_model_path()
    if mp:
        lines.append(f"[OK] 离线模型：{mp}")
    else:
        failed = True
        lines.append("[FAIL] 未找到离线语音识别模型")

    devs = audio.list_input_devices()
    if devs:
        lines.append(f"[OK] 麦克风 {len(devs)} 个，默认：{devs[0][1]}")
    else:
        lines.append("[WARN] 未检测到麦克风（一键对话 / 文字输入仍可用）")

    lines.append("自检结束：" + ("存在 FAIL，请查看上方条目" if failed else "全部通过"))
    _report(lines)
    return 1 if failed else 0
