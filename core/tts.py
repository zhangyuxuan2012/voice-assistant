# -*- coding: utf-8 -*-
"""语音播报。

- engine = "local"：Windows 本地语音合成（pyttsx3 / SAPI5），完全离线、零下载
- engine = "edge" ：微软 Edge 在线语音合成，音质更自然（需联网）
自动降级：所选引擎失败时自动尝试另一个，尽量保证能出声。
"""
import asyncio
import inspect
import os
import platform
import subprocess
import tempfile
import threading

_TTS_LOCK = threading.Lock()


def _speak_local(text):
    """Windows 本地 SAPI5 合成。成功返回 True。"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.say(text)
        engine.runAndWait()
        try:
            engine.stop()
        except Exception:
            pass
        return True
    except Exception:
        return False


def _speak_edge(text, voice):
    """微软在线合成。成功返回 True。"""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            result = communicate.save(path)
            # 兼容 edge-tts 6.x（协程）与 7.x（同步）
            if inspect.iscoroutine(result):
                asyncio.run(result)
            ok = _play_mp3(path)
        finally:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        return ok
    except Exception:
        return False


def _play_mp3(path):
    """播放 mp3。

    方案1：Windows 原生 winmm（mciSendString），零额外依赖；
    方案2：调用系统默认播放器。
    """
    if platform.system() == "Windows":
        try:
            import ctypes
            winmm = ctypes.windll.winmm
            winmm.mciSendStringW.argtypes = [
                ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p,
            ]
            winmm.mciSendStringW.restype = ctypes.c_uint
            alias = "va_audio"
            if winmm.mciSendStringW(
                    f'open "{path}" type mpegvideo alias {alias}', None, 0, None) == 0:
                try:
                    winmm.mciSendStringW(f"play {alias} wait", None, 0, None)
                finally:
                    winmm.mciSendStringW(f"close {alias}", None, 0, None)
                return True
        except Exception:
            pass
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def speak(text, engine="local", voice="zh-CN-XiaoxiaoNeural", block=False):
    """播报一段文字。默认后台线程播放，不阻塞界面。

    engine: local / edge
    """
    if not text:
        return

    def _run():
        with _TTS_LOCK:
            if engine == "edge":
                if not _speak_edge(text, voice):
                    _speak_local(text)
            else:
                if not _speak_local(text):
                    _speak_edge(text, voice)

    if block:
        _run()
    else:
        threading.Thread(target=_run, daemon=True, name="tts").start()
