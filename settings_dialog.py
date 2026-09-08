# -*- coding: utf-8 -*-
"""设置窗口：模型、语音、唤醒、热键等全部参数的可视化配置。"""
import threading

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QPushButton, QVBoxLayout,
)

import config
from core import audio, llm

TTS_VOICES = [
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-XiaoyiNeural",
    "zh-CN-YunjianNeural",
    "zh-CN-YunxiNeural",
    "zh-CN-YunyangNeural",
    "zh-CN-liaoning-XiaobeiNeural",
]

LANGUAGES = ["zh-CN", "en-US", "zh-HK", "ja-JP"]


class SettingsDialog(QDialog):
    test_done = pyqtSignal(str)  # 连接测试结果（跨线程安全）

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(520)
        self._cfg = dict(cfg)
        self.test_done.connect(self._show_test_result)
        self._build_ui()
        self._load_values(cfg)

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # 模型组
        model_box = QGroupBox("AI 模型")
        mf = QFormLayout(model_box)
        self.model_type = QComboBox()
        for key, label in config.MODEL_TYPE_LABELS.items():
            self.model_type.addItem(label, key)
        self.model_type.currentIndexChanged.connect(self._on_model_type_changed)
        self.api_key = QLineEdit()
        self.api_key.setPlaceholderText("本地模型可留空；云端模型填 API Key")
        self.base_url = QLineEdit()
        self.model_name = QLineEdit()
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setDecimals(1)
        self.system_prompt = QPlainTextEdit()
        self.system_prompt.setFixedHeight(70)
        mf.addRow("模型类型", self.model_type)
        mf.addRow("API Key", self.api_key)
        mf.addRow("接口地址 Base URL", self.base_url)
        mf.addRow("模型名称", self.model_name)
        mf.addRow("温度", self.temperature)
        mf.addRow("系统提示词", self.system_prompt)
        root.addWidget(model_box)

        # 语音组
        voice_box = QGroupBox("语音识别与播报")
        vf = QFormLayout(voice_box)
        self.stt_engine = QComboBox()
        self.stt_engine.addItem("离线识别（内置 vosk，零联网）", "offline")
        self.stt_engine.addItem("在线识别（Google，需联网更准）", "online")
        self.language = QComboBox()
        for lang in LANGUAGES:
            self.language.addItem(lang, lang)
        self.tts_engine = QComboBox()
        self.tts_engine.addItem("本地合成（Windows SAPI5，离线）", "local")
        self.tts_engine.addItem("微软在线合成（音质更好，需联网）", "edge")
        self.tts_voice = QComboBox()
        for v in TTS_VOICES:
            self.tts_voice.addItem(v, v)
        vf.addRow("语音识别", self.stt_engine)
        vf.addRow("识别语言", self.language)
        vf.addRow("语音播报", self.tts_engine)
        vf.addRow("播报音色", self.tts_voice)

        # 麦克风选择（可随意切换输入设备）
        mic_row = QHBoxLayout()
        self.mic_combo = QComboBox()
        self.mic_combo.setMinimumWidth(260)
        self.mic_refresh = QPushButton("刷新")
        self.mic_refresh.setFixedWidth(60)
        self.mic_refresh.clicked.connect(self._refresh_mics)
        mic_row.addWidget(self.mic_combo, 1)
        mic_row.addWidget(self.mic_refresh)
        self.mic_hint = QLabel("")
        self.mic_hint.setStyleSheet("color:#888;")
        vf.addRow("麦克风", mic_row)
        vf.addRow("", self.mic_hint)
        root.addWidget(voice_box)

        # 唤醒组
        wake_box = QGroupBox("唤醒与热键")
        wf = QFormLayout(wake_box)
        self.wake_enabled = QCheckBox("启用语音唤醒（说唤醒词即可对话）")
        self.wake_word = QLineEdit()
        self.wake_word.setMaxLength(20)
        self.hotkey = QLineEdit()
        self.hotkey.setPlaceholderText("例如：ctrl+alt+space")
        wf.addRow("", self.wake_enabled)
        wf.addRow("唤醒词", self.wake_word)
        wf.addRow("键盘热键", self.hotkey)
        root.addWidget(wake_box)

        # 测试按钮
        btns = QHBoxLayout()
        self.test_btn = QPushButton("测试 AI 连接")
        self.test_btn.clicked.connect(self._test_connection)
        self.test_hint = QLabel("")
        self.test_hint.setStyleSheet("color:#888;")
        btns.addWidget(self.test_btn)
        btns.addWidget(self.test_hint, 1)
        root.addLayout(btns)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ---------------- 逻辑 ----------------
    def _on_model_type_changed(self):
        key = self.model_type.currentData()
        preset = config.MODEL_PRESETS.get(key, {})
        if key == "custom":
            return
        if preset.get("base_url"):
            self.base_url.setText(preset["base_url"])
        if preset.get("model_name"):
            self.model_name.setText(preset["model_name"])
        if key in ("ollama", "lm_studio"):
            self.api_key.setPlaceholderText("本地模型无需 Key，可留空")
        else:
            self.api_key.setPlaceholderText("请输入你的 API Key")

    def _load_values(self, cfg):
        idx = self.model_type.findData(cfg["model_type"])
        self.model_type.setCurrentIndex(idx if idx >= 0 else 0)
        self.api_key.setText(cfg.get("api_key", ""))
        self.base_url.setText(cfg.get("base_url", ""))
        self.model_name.setText(cfg.get("model_name", ""))
        self.temperature.setValue(float(cfg.get("temperature", 0.7)))
        self.system_prompt.setPlainText(cfg.get("system_prompt", ""))
        self._set_combo(self.stt_engine, cfg.get("stt_engine", "offline"))
        self._set_combo(self.language, cfg.get("language", "zh-CN"))
        self._set_combo(self.tts_engine, cfg.get("tts_engine", "local"))
        self._set_combo(self.tts_voice, cfg.get("tts_voice", "zh-CN-XiaoxiaoNeural"))
        self.wake_enabled.setChecked(bool(cfg.get("wake_enabled", True)))
        self.wake_word.setText(cfg.get("wake_word", "嗨,贾维斯"))
        self.hotkey.setText(cfg.get("hotkey", "ctrl+alt+space"))
        self._refresh_mics(cfg.get("mic_device", -1))

    def _refresh_mics(self, selected=-1):
        """枚举可用麦克风填入下拉框；selected 为当前配置的设备索引。"""
        try:
            devs = audio.list_input_devices()
        except Exception:
            devs = []
        self.mic_combo.clear()
        self.mic_combo.addItem("系统默认", -1)
        for i, name in devs:
            self.mic_combo.addItem(f"{name}", i)
        # 恢复选中项
        target = selected if selected in [i for _, i in devs] else -1
        for k in range(self.mic_combo.count()):
            if self.mic_combo.itemData(k) == target:
                self.mic_combo.setCurrentIndex(k)
                break
        if not devs:
            self.mic_hint.setText("未检测到麦克风")
        else:
            self.mic_hint.setText(f"共 {len(devs)} 个输入设备")

    @staticmethod
    def _set_combo(combo, value):
        idx = combo.findData(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _test_connection(self):
        self.test_btn.setEnabled(False)
        self.test_hint.setText("测试中…")

        def _run():
            try:
                client = llm.LLMClient(
                    self.model_type.currentData(),
                    self.api_key.text().strip(),
                    self.base_url.text().strip(),
                    self.model_name.text().strip(),
                )
                ok, msg = client.test()
                result = ("✅ " + msg) if ok else ("❌ " + msg)
            except llm.LLMError as e:
                result = "❌ " + str(e)
            except Exception as e:
                result = f"❌ 发生错误：{e}"
            self.test_done.emit(result)

        threading.Thread(target=_run, daemon=True).start()

    def _show_test_result(self, result):
        self.test_hint.setText(result[:80])
        self.test_btn.setEnabled(True)
        QMessageBox.information(self, "连接测试", result)

    def get_result(self):
        """返回更新后的配置 dict。"""
        cfg = dict(self._cfg)
        cfg["model_type"] = self.model_type.currentData()
        cfg["api_key"] = self.api_key.text().strip()
        cfg["base_url"] = self.base_url.text().strip()
        cfg["model_name"] = self.model_name.text().strip()
        cfg["temperature"] = self.temperature.value()
        cfg["system_prompt"] = self.system_prompt.toPlainText().strip()
        cfg["stt_engine"] = self.stt_engine.currentData()
        cfg["language"] = self.language.currentData()
        cfg["tts_engine"] = self.tts_engine.currentData()
        cfg["tts_voice"] = self.tts_voice.currentData()
        cfg["wake_enabled"] = self.wake_enabled.isChecked()
        cfg["wake_word"] = self.wake_word.text().strip() or "嗨,贾维斯"
        cfg["hotkey"] = self.hotkey.text().strip() or "ctrl+alt+space"
        cfg["mic_device"] = int(self.mic_combo.currentData() or -1)
        return cfg
