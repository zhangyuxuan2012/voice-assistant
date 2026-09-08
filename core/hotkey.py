# -*- coding: utf-8 -*-
"""全局键盘热键监听（使用 keyboard 库）。

热键触发时在 keyboard 库内部线程调用回调，不阻塞 GUI。
注册失败会把原因写入 self.error，便于界面提示。
"""
import threading


class HotkeyListener:
    def __init__(self, hotkey, callback):
        self._hotkey = hotkey
        self._callback = callback
        self._thread = None
        self._running = False
        self.error = None

    def start(self):
        """启动监听线程。成功返回 True。"""
        if self._running:
            return True
        try:
            import keyboard
        except Exception as e:
            self.error = f"热键组件加载失败：{e}"
            return False
        self._running = True
        self._thread = threading.Thread(target=self._run, args=(keyboard,),
                                        daemon=True, name="hotkey")
        self._thread.start()
        return True

    def _run(self, keyboard):
        try:
            keyboard.add_hotkey(self._hotkey, self._on_press, suppress=True)
            keyboard.wait()  # 阻塞直到所有热键被移除
        except Exception as e:
            self.error = f"热键注册失败：{e}"
        finally:
            self._running = False

    def _on_press(self):
        if self._callback:
            try:
                self._callback()
            except Exception:
                pass

    def stop(self):
        self._running = False
        try:
            import keyboard
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
