# 🎙️ 语音助手 VoiceAssistant

> 一款**无需任何配置、双击即可运行**的桌面语音 AI 助手。支持语音唤醒、一键对话、全局热键、麦克风切换，默认接入 APIHub（agnes 云端模型，开箱即用），也可切换本地模型（Ollama / LM Studio）或任意 OpenAI 兼容接口。**零下载、离线可用、多轮对话**。

---

## ✨ 功能特性

| 功能 | 说明 |
| --- | --- |
| 🗣️ 语音唤醒 | 说“**嗨，贾维斯**”（默认，可自定义）即可开始对话 |
| 🎤 一键对话 | 点击“🎤 一键对话”按钮，直接说话提问 |
| ⌨️ 全局热键 | 默认 `Ctrl + Alt + Space`，可自定义 |
| ⌨️ 文字输入 | 无麦克风也能用，输入文字与 AI 对话 |
| 🎙️ 麦克风切换 | “设置”里可随意切换任意输入设备 |
| 🧠 本地模型 | 接入本机 Ollama / LM Studio，数据不出本机 |
| ☁️ 云端模型 | APIHub（默认）/ OpenAI / 硅基流动 / DeepSeek / 任意 OpenAI 兼容接口 |
| 📴 离线优先 | 内置离线语音识别模型 + Windows 本地语音合成，断网可用 |
| 💬 多轮对话 | 自动记住上下文，连续提问不打断 |
| 🎨 图形界面 | PyQt6 深色界面，对话与状态一目了然 |

---

## 🚀 快速开始（最终用户）

1. 下载发布包 `VoiceAssistant-vX.X.X-win64.zip`
2. 解压后双击 **`VoiceAssistant.exe`**
3. 完成！无需安装 Python、无需下载任何东西

**开箱即用：** 默认已接入 APIHub（agnes-3.0-flash）并预填 API Key，双击即可对话。
如需更换：

- **换云端模型**：打开“⚙ 设置”，选择厂商（OpenAI / 硅基流动 / DeepSeek / 自定义），填入 API Key；
- **本地模型（Ollama）**：先启动 Ollama（`ollama run qwen2.5:7b`），设置中切到 Ollama；
- **本地模型（LM Studio）**：启动 LM Studio 并加载模型，打开开发者模式。

设置完成后点击“测试 AI 连接”验证，然后“保存”。

---

## 📖 使用说明

| 操作 | 方式 |
| --- | --- |
| 语音唤醒 | 对着麦克风说“**嗨，贾维斯**”，听到提示后说出你的问题 |
| 一键对话 | 点击 **“🎤 一键对话”** 按钮，然后说话 |
| 键盘热键 | 按 **`Ctrl + Alt + Space`**，然后说话 |
| 文字对话 | 在底部输入框打字，回车发送 |
| 修改设置 | 菜单“设置 → 打开设置…”，或点击“⚙ 设置”按钮 |
| 退出 | 点击“关闭”按钮，或菜单“设置 → 退出” |

> 语音播报默认使用 Windows 本地合成（完全离线）。若想获得更自然的音色，
> 可在设置中把“语音播报”改为“微软在线合成”（需联网）。

---

## 🧩 支持的 AI 模型

| 类型 | 厂商/后端 | Base URL | 需要 API Key |
| --- | --- | --- | --- |
| 云端（默认） | APIHub agnes | `https://apihub.agnes-ai.com/v1` | 是（已预填） |
| 本地 | Ollama | `http://localhost:11434/v1` | 否 |
| 本地 | LM Studio | `http://localhost:1234/v1` | 否 |
| 云端 | OpenAI | `https://api.openai.com/v1` | 是 |
| 云端 | 硅基流动 SiliconFlow | `https://api.siliconflow.cn/v1` | 是 |
| 云端 | DeepSeek | `https://api.deepseek.com/v1` | 是 |
| 自定义 | 任意 OpenAI 兼容接口 | 自填 | 视服务而定 |

> 只需遵循 OpenAI Chat Completions 接口即可接入，兼容市面上绝大多数模型服务。

---

## 🏗️ 从源码构建（开发者）

```bat
:: 1. 准备
git clone https://github.com/zhangyuxuan2012/voice-assistant.git
cd voice-assistant

:: 2. 一键构建（自动装依赖、下载离线模型、打包 EXE）
build_exe.bat
```

产物位于 `dist/VoiceAssistant.exe`，即为内置全部依赖与离线模型的单文件可执行程序。

也可以直接运行源码：

```bat
python -m pip install -r requirements.txt
python tools\prepare_models.py     :: 下载离线识别模型（开发者构建用）
python main.py                     :: 运行
python main.py --selftest          :: 运行自检
```

---

## 🗂️ 项目结构

```
voice_assistant/
├── main.py                # 主程序（GUI + 会话逻辑）
├── config.py              # 默认配置与读写
├── settings_dialog.py     # 设置窗口
├── selftest.py            # 自检模块
├── make_icon.py           # 生成图标（可选）
├── requirements.txt       # 依赖清单
├── version_info.txt       # EXE 版本信息
├── setup.bat              # 一键启动（成品包内）
├── build_exe.bat          # 一键构建脚本（开发者）
├── voice_assistant.ico    # 应用图标
├── core/
│   ├── audio.py           # 语音采集 + 识别（离线 vosk / 在线 Google）
│   ├── llm.py             # AI 模型调用（OpenAI 兼容）
│   ├── tts.py             # 语音播报（本地 SAPI5 / 微软在线）
│   ├── hotkey.py          # 全局键盘热键
│   ├── wake.py            # 语音唤醒词监听
│   └── paths.py           # 资源路径（源码/打包兼容）
└── tools/
    └── prepare_models.py  # 下载离线识别模型（构建用）
```

---

## 🧪 自检

打包后可用以下命令验证环境完整性（结果写入 `%APPDATA%/VoiceAssistant/selftest.txt`）：

```bat
VoiceAssistant.exe --selftest
```

---

## 📌 常见问题

- **本地模型调用失败？** 确认 Ollama / LM Studio 已启动且模型已拉取；设置里点“测试 AI 连接”。
- **离线识别不准确？** 离线模型体积小、识别率有限；对准确率要求高可改用“在线识别（Google）”。
- **热键无反应？** 部分环境需要以管理员身份运行；也可改用“一键对话”按钮。
- **杀毒软件误报？** 单文件打包的程序偶尔被误报，加入白名单即可（本项目开源，可自行校验）。
- **配置存在哪里？** `%APPDATA%/VoiceAssistant/config.json`，日志在同目录。
- **⚠️ API Key 安全：** 源码 `config.py` 中预填的 Key 仅用于本地默认体验，**上传 GitHub 前请务必删除或替换**（改成空字符串，让用户自己在设置里填）；你的 Key 保存在本机 `%APPDATA%`，不会上传。

---

## 📜 开源协议

本项目基于 [MIT License](LICENSE) 开源，欢迎 Fork、Star、提 Issue 与 PR。

> 附带声明：本项目仅调用用户自行选择的模型服务，不内置任何模型权重；
> 语音识别离线模型（Vosk）遵循其各自的开源许可，详见其官方仓库。
