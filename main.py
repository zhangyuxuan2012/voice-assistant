# -*- coding: utf-8 -*-
"""语音助手 —— 主程序。

一款无需任何配置、双击即可使用的桌面语音助手：
  - 语音唤醒（自定义唤醒词） / 一键对话按钮 / 全局键盘热键
  - 接入本地模型（Ollama / LM Studio）或云端模型（OpenAI 兼容，只需 API Key）
  - 离线优先：内置离线语音识别模型与本地语音合成，零下载直接运行
  - 多轮对话，全部内容在图形界面展示

启动方式：
  python main.py            # 图形界面
  python main.py --selftest # 运行自检
"""
import os
import sys
import threading
import traceback

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMenu, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

import config
from core import audio, llm, paths as core_paths, tts
from core.hotkey import HotkeyListener
from core.wake import WakeListener
from settings_dialog import SettingsDialog

DARK_QSS = """
QMainWindow, QDialog { background:#1c1d22; }
QLabel { color:#e8e8ea; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background:#26272e; color:#e8e8ea; border:1px solid #3a3b45; border-radius:6px;
    padding:4px 6px; selection-background-color:#3b82f6;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border:1px solid #3b82f6; }
QPushButton {
    background:#2f3138; color:#e8e8ea; border:1px solid #41424e; border-radius:6px;
    padding:6px 14px;
}
QPushButton:hover { background:#3a3d46; }
QPushButton:pressed { background:#26272e; }
QPushButton:disabled { color:#777; }
QPushButton#primary {
    background:#2563eb; border:1px solid #3b82f6; color:white; font-weight:bold;
}
QPushButton#primary:hover { background:#3b82f6; }
QPushButton#danger { background:#7f1d1d; border:1px solid #b91c1c; color:white; }
QPushButton#danger:hover { background:#991b1b; }
QMenuBar { background:#1c1d22; color:#e8e8ea; }
QMenuBar::item:selected { background:#3a3d46; }
QMenu { background:#26272e; color:#e8e8ea; border:1px solid #3a3b45; }
QMenu::item:selected { background:#3b82f6; }
QStatusBar { background:#15161a; color:#aaa; }
QGroupBox { color:#e8e8ea; border:1px solid #3a3b45; border-radius:8px; margin-top:10px; }
QGroupBox::title { subcontrol-origin: margin; left:10px; padding:0 4px; color:#9aa0ab; }
"""


def _write_log(msg):
    try:
        with open(os.path.join(config.app_data_dir(), "voice_assistant.log"),
                  "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _install_excepthook():
    def hook(exc_type, exc, tb):
        try:
            _write_log("".join(traceback.format_exception(exc_type, exc, tb)))
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc, tb)
    sys.excepthook = hook


class Assistant(QObject):
    """语音助手核心逻辑：唤醒、识别、AI 对话、语音播报。"""

    log = pyqtSignal(str, str)      # (kind, text)  kind: user/ai/sys/err/ok
    status = pyqtSignal(str)        # 状态栏文字
    busy = pyqtSignal(bool)         # 是否忙碌

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg = config.load_config()
        self.messages = [{"role": "system",
                          "content": self.cfg.get("system_prompt") or config.DEFAULT_SYSTEM_PROMPT}]
        self.wake = None
        self.hotkey = None
        self._session_lock = threading.Lock()
        self._busy = False
        self._restart_backends()
        self._warm_model_cache()

    # ---------------- 后端控制 ----------------
    def _restart_backends(self):
        self._stop_backends()
        cfg = self.cfg

        has_mic = bool(audio.list_input_devices())
        mic_dev = cfg.get("mic_device", -1)
        if cfg.get("wake_enabled", True) and has_mic:
            self.wake = WakeListener(cfg.get("wake_word", "嗨,贾维斯"),
                                     self._on_wake_word,
                                     cfg.get("stt_engine", "offline"),
                                     cfg.get("language", "zh-CN"),
                                     mic_dev)
            self.wake.start()
            self.status.emit(f"🎧 语音唤醒已开启（唤醒词：“{cfg.get('wake_word')}”）")
        elif not has_mic:
            self.status.emit("⚠️ 未检测到麦克风，可点击“🎤 一键对话”或使用文字输入")

        try:
            self.hotkey = HotkeyListener(cfg.get("hotkey", "ctrl+alt+space"), self.on_hotkey)
            if not self.hotkey.start():
                self.status.emit(f"⚠️ {self.hotkey.error}")
        except Exception as e:
            self.status.emit(f"⚠️ 热键注册失败：{e}")

    def _stop_backends(self):
        if self.wake is not None:
            try:
                self.wake.stop()
            except Exception:
                pass
            self.wake = None
        if self.hotkey is not None:
            try:
                self.hotkey.stop()
            except Exception:
                pass
            self.hotkey = None

    def apply_settings(self, new_cfg):
        self.cfg = new_cfg
        self.messages = [{"role": "system",
                          "content": self.cfg.get("system_prompt") or config.DEFAULT_SYSTEM_PROMPT}]
        config.save_config(new_cfg)
        self._restart_backends()

    def _warm_model_cache(self):
        """若 EXE 内置了离线模型，首次启动时复制一份到用户目录，加速后续启动。"""

        def _run():
            try:
                src = os.path.join(core_paths.resource_path("models"), "vosk-model-small-cn-0.22")
                dst = os.path.join(config.app_data_dir(), "models", "vosk-model-small-cn-0.22")
                if os.path.isdir(src) and os.path.exists(os.path.join(src, "am", "final.mdl")):
                    if not (os.path.isdir(dst) and os.path.exists(os.path.join(dst, "am", "final.mdl"))):
                        import shutil
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copytree(src, dst, dirs_exist_ok=True)
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True, name="model-cache").start()

    # ---------------- 会话 ----------------
    def _on_wake_word(self, _text):
        self.log.emit("sys", "🎤 检测到唤醒词，请说出你的问题…")
        self.start_session()

    def on_hotkey(self):
        self.start_session()

    def start_session(self):
        """一键对话：麦克风听一句 → AI 回答 → 语音播报。"""
        threading.Thread(target=self._session_worker, daemon=True,
                         name="session").start()

    def _session_worker(self):
        if not self._session_lock.acquire(blocking=False):
            self.status.emit("⏳ 正在处理上一条，请稍候…")
            return
        try:
            self._set_busy(True)
            if self.wake is not None:
                self.wake.pause()
            self.status.emit("🎤 请说话…")
            text = audio.listen_once(engine=self.cfg.get("stt_engine", "offline"),
                                     language=self.cfg.get("language", "zh-CN"),
                                     timeout=8, phrase_time_limit=15,
                                     device=self.cfg.get("mic_device", -1))
            if not text:
                self.status.emit("❌ 没有听清，请再试一次")
                return
            self.log.emit("user", f"🧑 我：{text}")
            self._ask_and_speak(text)
        finally:
            if self.wake is not None:
                self.wake.resume()
            self._set_busy(False)
            self.status.emit("🎧 就绪")

    def ask_text(self, text):
        """文字输入对话。"""
        text = (text or "").strip()
        if not text:
            return
        self.log.emit("user", f"🧑 我：{text}")
        threading.Thread(target=self._ask_text_worker, args=(text,),
                         daemon=True, name="text-session").start()

    def _ask_text_worker(self, text):
        if not self._session_lock.acquire(blocking=False):
            self.status.emit("⏳ 正在处理上一条，请稍候…")
            return
        try:
            self._ask_and_speak(text)
        finally:
            self._session_lock.release()

    def _ask_and_speak(self, text):
        self.messages.append({"role": "user", "content": text})
        self._trim_history()
        try:
            client = llm.LLMClient(self.cfg.get("model_type", "ollama"),
                                   self.cfg.get("api_key", ""),
                                   self.cfg.get("base_url", ""),
                                   self.cfg.get("model_name", ""))
            self.status.emit("🤖 AI 思考中…")
            reply = client.chat(self.messages,
                                temperature=self.cfg.get("temperature", 0.7))
        except llm.LLMError as e:
            self.messages.pop()
            self.log.emit("err", f"⚠️ {e}")
            self.status.emit("⚠️ 模型调用失败，请检查“⚙ 设置”")
            return
        except Exception as e:
            self.messages.pop()
            self.log.emit("err", f"⚠️ 发生错误：{e}")
            self.status.emit("⚠️ 模型调用失败")
            return

        self.messages.append({"role": "assistant", "content": reply})
        self.log.emit("ai", f"🤖 助手：{reply}")
        self.status.emit("🔊 语音播报中…")
        tts.speak(reply, engine=self.cfg.get("tts_engine", "local"),
                  voice=self.cfg.get("tts_voice", "zh-CN-XiaoxiaoNeural"))

    def _trim_history(self):
        # 保留 system + 最近最多 40 条消息（约 20 轮），防止上下文无限增长
        if len(self.messages) > 40:
            self.messages = [self.messages[0]] + self.messages[-39:]

    def _set_busy(self, value):
        self._busy = value
        self.busy.emit(value)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.assistant = Assistant()
        self._build_ui()
        self.assistant.log.connect(self._append_log)
        self.assistant.status.connect(self.status_label.setText)
        self.assistant.busy.connect(self._on_busy)
        self._print_startup()

    # ---------------- UI ----------------
    def _build_ui(self):
        self.setWindowTitle(f"语音助手 v{config.APP_VERSION}")
        icon_path = core_paths.resource_path("voice_assistant.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(760, 580)
        self.setMinimumSize(560, 460)
        self.setStyleSheet(DARK_QSS)

        # 菜单栏
        menubar = self.menuBar()
        m_settings = menubar.addMenu("设置")
        a_open = m_settings.addAction("打开设置…")
        a_open.triggered.connect(self.open_settings)
        self.a_top = m_settings.addAction("窗口置顶")
        self.a_top.setCheckable(True)
        self.a_top.setChecked(bool(self.assistant.cfg.get("always_on_top", True)))
        self.a_top.triggered.connect(self._toggle_top)
        m_settings.addSeparator()
        a_exit = m_settings.addAction("退出")
        a_exit.triggered.connect(self.close)

        m_help = menubar.addMenu("帮助")
        a_usage = m_help.addAction("使用说明")
        a_usage.triggered.connect(self.show_usage)
        a_about = m_help.addAction("关于")
        a_about.triggered.connect(self.show_about)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 6, 10, 10)

        # 标题 + 状态
        head = QHBoxLayout()
        title = QLabel("🎙️ 语音助手")
        title.setStyleSheet("font-size:17px; font-weight:bold; color:#e8e8ea;")
        head.addWidget(title)
        head.addStretch(1)
        self.status_label = QLabel("正在初始化…")
        self.status_label.setStyleSheet("color:#9aa0ab;")
        head.addWidget(self.status_label)
        root.addLayout(head)

        # 聊天区
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setFont(QFont("Microsoft YaHei", 11))
        self.chat.setStyleSheet(
            "QTextEdit{background:#15161a; color:#e8e8ea; border:1px solid #3a3b45;"
            "border-radius:8px; padding:8px;}")
        root.addWidget(self.chat, 1)

        # 文字输入行
        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("也可以直接输入文字与 AI 对话（回车发送）")
        self.input.returnPressed.connect(self._send_text)
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self._send_text)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_btn)
        root.addLayout(input_row)

        # 按钮行
        btn_row = QHBoxLayout()
        self.talk_btn = QPushButton("🎤 一键对话")
        self.talk_btn.setObjectName("primary")
        self.talk_btn.clicked.connect(self.assistant.start_session)
        self.settings_btn = QPushButton("⚙ 设置")
        self.settings_btn.clicked.connect(self.open_settings)
        self.close_btn = QPushButton("关闭")
        self.close_btn.setObjectName("danger")
        self.close_btn.clicked.connect(self.close)
        btn_row.addWidget(self.talk_btn)
        btn_row.addWidget(self.settings_btn)
        btn_row.addWidget(self.close_btn)
        root.addLayout(btn_row)

        self.setCentralWidget(central)
        self._apply_top(bool(self.assistant.cfg.get("always_on_top", True)))

    def _apply_top(self, on):
        flags = self.windowFlags()
        if on:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def _toggle_top(self, checked):
        self._apply_top(checked)
        cfg = self.assistant.cfg
        cfg["always_on_top"] = checked
        config.save_config(cfg)

    # ---------------- 事件 ----------------
    def _append_log(self, kind, text):
        color = {
            "user": "#7dd3fc",   # 用户：浅蓝
            "ai": "#86efac",     # 助手：浅绿
            "err": "#fca5a5",    # 错误：浅红
            "ok": "#fde68a",     # 成功：浅黄
        }.get(kind, "#e8e8ea")
        self.chat.append(f'<span style="color:{color}">{_esc(text)}</span>')
        sb = self.chat.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_busy(self, busy):
        self.talk_btn.setEnabled(not busy)
        self.send_btn.setEnabled(not busy)

    def _send_text(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.assistant.ask_text(text)

    def _print_startup(self):
        cfg = self.assistant.cfg
        lines = [
            ("ok", f"✅ 语音助手 v{config.APP_VERSION} 已启动"),
            ("sys", f"模型：{config.MODEL_TYPE_LABELS.get(cfg['model_type'], cfg['model_type'])}"
                    f"（{cfg['model_name']}）"),
            ("sys", f"语音识别：{'离线' if cfg['stt_engine'] == 'offline' else '在线'}　"
                    f"语音播报：{'本地' if cfg['tts_engine'] == 'local' else '微软在线'}"),
            ("sys", f"唤醒方式：说“{cfg['wake_word']}” / 按 {cfg['hotkey']} / 点击“🎤 一键对话”"),
        ]
        for kind, text in lines:
            self._append_log(kind, text)

    # ---------------- 菜单动作 ----------------
    def open_settings(self):
        dlg = SettingsDialog(self.assistant.cfg, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.assistant.apply_settings(dlg.get_result())
            self._append_log("ok", "✅ 设置已保存并生效")

    def show_usage(self):
        QMessageBox.information(self, "使用说明",
            "🎙️ 语音助手\n\n"
            "【唤醒方式】\n"
            "1. 语音唤醒：说“嗨，贾维斯”（可自定义），然后说出你的问题\n"
            "2. 一键对话：点击“🎤 一键对话”按钮，直接说话\n"
            "3. 键盘热键：默认 Ctrl+Alt+Space\n"
            "4. 文字输入：在下框输入文字，回车发送\n\n"
            "【AI 模型】\n"
            "在“设置”中选择模型类型。本地模型需先自行启动 "
            "Ollama / LM Studio；云端模型只需填写 API Key。\n\n"
            "【麦克风】\n"
            "在“设置”→“麦克风”下拉框中可随意切换输入设备。\n\n"
            "【离线使用】\n"
            "语音识别与播报均内置离线能力，断网也能用（云端模型除外）。")

    def show_about(self):
        QMessageBox.about(self, "关于",
            f"语音助手 v{config.APP_VERSION}\n\n"
            "双击即用 · 零配置 · 支持离线\n"
            "开源协议：MIT")

    def closeEvent(self, event):
        try:
            self.assistant._stop_backends()
        except Exception:
            pass
        event.accept()


def _esc(text):
    """HTML 转义，防止特殊字符破坏样式。"""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("\n", "<br>"))


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("语音助手")

    if len(sys.argv) > 1 and sys.argv[1] in ("--selftest", "--self-test"):
        import selftest
        code = selftest.run_selftest()
        sys.exit(code)

    _install_excepthook()
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
