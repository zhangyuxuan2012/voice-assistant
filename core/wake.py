# -*- coding: utf-8 -*-
"""后台语音唤醒词监听。

循环采集麦克风语音，命中唤醒词后暂停监听，并在同一线程回调 on_wake。
外部（主程序）执行完一轮会话后调用 resume() 恢复监听。
"""
import threading
import time

from . import audio


# ------------------------------------------------------------------ 匹配
def _normalize(text):
    """去掉空白与中英文标点，用于唤醒词模糊匹配。

    例：'嗨 贾维斯' / '嗨，贾维斯' / '嗨,贾维斯' 均归一化为 '嗨贾维斯'。
    """
    import re
    text = (text or "").strip().lower()
    return re.sub(r"[\s\u3000，。！？、；：,.!?;:'\"“”‘’\-_—]+", "", text)


class WakeListener:
    def __init__(self, wake_word, on_wake, stt_engine="offline", language="zh-CN",
                 device=None):
        self.wake_word = (wake_word or "").strip().lower()
        self.wake_key = _normalize(self.wake_word)  # 归一化后的匹配串
        self.on_wake = on_wake
        self.stt_engine = stt_engine
        self.language = language
        self.device = device  # 麦克风索引；None 表示系统默认
        self._running = False
        self._paused = False
        self._lock = threading.Lock()

    # ---------------- 状态控制 ----------------
    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._paused = False
        threading.Thread(target=self._loop, daemon=True, name="wake-listener").start()

    def stop(self):
        with self._lock:
            self._running = False
            self._paused = False

    def pause(self):
        with self._lock:
            self._paused = True

    def resume(self):
        with self._lock:
            self._paused = False

    def _is_running(self):
        with self._lock:
            return self._running

    def _is_paused(self):
        with self._lock:
            return self._paused

    # ---------------- 主循环 ----------------
    def _loop(self):
        while self._is_running():
            if self._is_paused():
                time.sleep(0.15)
                continue

            text = audio.listen_once(engine=self.stt_engine, language=self.language,
                                     timeout=1.8, phrase_time_limit=4.0,
                                     device=self.device)

            # 会话可能已开始（如热键触发），丢弃本次结果
            if self._is_paused():
                continue
            if not text:
                continue
            if self.wake_key and self.wake_key in _normalize(text):
                self.pause()
                try:
                    self.on_wake(text)
                except Exception:
                    pass
                # 恢复监听由主程序在会话结束后调用 resume()
