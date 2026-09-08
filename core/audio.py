# -*- coding: utf-8 -*-
"""语音采集与识别。

- 采集使用 sounddevice（无需 PyAudio，兼容新版本 Python / 免去额外依赖）。
- 识别支持两种引擎：
    * offline：vosk 本地模型（EXE 已内置，完全离线，零下载）
    * online ：Google Web Speech API（需联网，中文识别准确率更高）
"""
import json
import os
import threading
import time
import urllib.request
import zipfile

import numpy as np
import sounddevice as sd

from . import paths

# vosk 需要 16kHz、单声道、16bit 的 PCM 数据
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
BLOCK = 1600  # 每个音频块 0.1 秒

VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip"

_MIC_LOCK = threading.Lock()
_model_lock = threading.Lock()
_model = None
_model_error = None


# ------------------------------------------------------------------ 麦克风
def list_input_devices():
    """返回可用输入设备列表 [(index, name), ...]；无麦克风返回空列表。"""
    try:
        devs = sd.query_devices()
        return [(i, d.get("name", f"设备 {i}"))
                for i, d in enumerate(devs)
                if d.get("max_input_channels", 0) > 0]
    except Exception:
        return []


def resolve_input_device(device_idx):
    """把配置里的麦克风索引解析为 sounddevice 可用值。

    -1 / None / 无效索引 → None（系统默认麦克风）。
    """
    try:
        idx = int(device_idx)
        if idx >= 0:
            # 校验索引是否真的是可用的输入设备，避免无效值导致采集失败
            devs = sd.query_devices()
            if 0 <= idx < len(devs) and devs[idx].get("max_input_channels", 0) > 0:
                return idx
        return None
    except Exception:
        return None


def _has_input(device=None):
    try:
        idx = resolve_input_device(device)
        if idx is None:
            idx = sd.default.device[0]
        return idx is not None and idx >= 0
    except Exception:
        return False


def _calibrate_noise(stream, seconds=0.4):
    """采集一小段环境噪音，返回背景能量均值。"""
    energies = []
    blocks = max(int(seconds * SAMPLE_RATE / BLOCK), 1)
    try:
        for _ in range(blocks):
            data, _ = stream.read(BLOCK)
            energies.append(float(np.sqrt(np.mean(np.square(data.astype(np.float32))))))
    except Exception:
        pass
    return float(np.mean(energies)) if energies else 300.0


def record_phrase(timeout=8.0, phrase_time_limit=15.0, silence=0.8, start_silence=0.4,
                  device=None):
    """录制一段完整语音（自动检测起止），返回 int16/16k/单声道 bytes。

    device：麦克风索引（来自“设置”里的麦克风下拉框）；None 表示系统默认。
    流程：环境噪音校准 → 等待说话（≤timeout）→ 录制直到静音（≤phrase_time_limit）。
    未检测到说话或出错时返回 None。
    """
    if not _has_input(device):
        return None
    with _MIC_LOCK:
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                                dtype=DTYPE, blocksize=BLOCK,
                                device=resolve_input_device(device)) as stream:
                noise = _calibrate_noise(stream, start_silence)
                threshold = max(noise * 1.8, 350.0)

                # 阶段一：等待说话开始
                started = time.time()
                speaking = False
                frames = []
                while time.time() - started < timeout:
                    data, _ = stream.read(BLOCK)
                    energy = float(np.sqrt(np.mean(np.square(data.astype(np.float32)))))
                    if energy > threshold:
                        frames.append(data)
                        speaking = True
                        break
                if not speaking:
                    return None

                # 阶段二：录制直到静音或超时
                silence_blocks = 0
                speak_start = time.time()
                while True:
                    data, _ = stream.read(BLOCK)
                    frames.append(data)
                    energy = float(np.sqrt(np.mean(np.square(data.astype(np.float32)))))
                    if energy > threshold:
                        silence_blocks = 0
                    else:
                        silence_blocks += 1
                        if silence_blocks * (BLOCK / SAMPLE_RATE) >= silence:
                            break
                    if (time.time() - speak_start) >= phrase_time_limit:
                        break

                audio = np.concatenate(frames) if len(frames) > 1 else frames[0]
                return audio.tobytes()
        except Exception:
            return None


# ------------------------------------------------------------------ 离线识别
def offline_model_ready():
    """离线模型是否就绪。"""
    return paths.vosk_model_path() is not None


def _load_vosk_model():
    """加载 vosk 模型（线程安全，仅加载一次）。返回 (model, error)。"""
    global _model, _model_error
    with _model_lock:
        if _model is not None:
            return _model, None
        if _model_error is not None:
            return None, _model_error
        try:
            from vosk import Model, SetLogLevel
            SetLogLevel(0)  # 静默 vosk 内部日志
            path = paths.vosk_model_path()
            if not path:
                _model_error = "未找到离线语音识别模型"
                return None, _model_error
            _model = Model(path)
            return _model, None
        except Exception as e:
            _model_error = f"离线模型加载失败：{e}"
            return None, _model_error


def offline_recognize(raw_bytes, language="zh"):
    """用 vosk 离线识别一段 PCM。返回 (text, error)；text 可能为 None。"""
    model, err = _load_vosk_model()
    if model is None:
        return None, err
    try:
        from vosk import KaldiRecognizer
        rec = KaldiRecognizer(model, SAMPLE_RATE)
        rec.AcceptWaveform(raw_bytes)
        res = json.loads(rec.FinalResult())
        text = (res.get("text") or "").strip()
        return (text if text else None), None
    except Exception as e:
        return None, f"离线识别失败：{e}"


def online_recognize(raw_bytes, language="zh-CN"):
    """用 Google Web Speech API 在线识别一段 PCM。返回 (text, error)。"""
    try:
        import speech_recognition as sr
        audio_data = sr.AudioData(raw_bytes, SAMPLE_RATE, 2)
        recognizer = sr.Recognizer()
        text = recognizer.recognize_google(audio_data, language=language)
        text = (text or "").strip()
        return (text if text else None), None
    except sr.UnknownValueError:
        return None, None
    except Exception as e:
        return None, f"在线识别失败：{e}"


def recognize(raw_bytes, engine="offline", language="zh-CN"):
    """统一识别入口。返回 (text, error)。"""
    if engine == "online":
        return online_recognize(raw_bytes, language)
    return offline_recognize(raw_bytes)


def listen_once(engine="offline", language="zh-CN", timeout=8.0, phrase_time_limit=15.0,
                device=None):
    """录制并识别一句语音，返回文字；失败返回 None。"""
    raw = record_phrase(timeout=timeout, phrase_time_limit=phrase_time_limit, device=device)
    if raw is None:
        return None
    text, _ = recognize(raw, engine, language)
    return text


def download_vosk_model(progress_cb=None):
    """下载并解压离线模型到用户目录（仅源码运行 / 模型缺失时使用）。

    返回 (ok, path_or_error)。
    """
    target_dir = paths.vosk_model_download_dir()
    try:
        os.makedirs(target_dir, exist_ok=True)
        dest = os.path.join(target_dir, "vosk-model-small-cn-0.22")
        if os.path.isdir(dest) and os.path.exists(os.path.join(dest, "am", "final.mdl")):
            return True, dest

        zip_path = os.path.join(target_dir, "vosk-model-small-cn-0.22.zip")
        tmp = zip_path + ".part"
        if progress_cb:
            progress_cb(0.0, "正在下载离线语音识别模型…")
        req = urllib.request.Request(VOSK_MODEL_URL, headers={"User-Agent": "VoiceAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as f:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress_cb and total:
                    progress_cb(done / total, f"正在下载离线语音识别模型… {done // 1024 // 1024} MB")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        os.rename(tmp, zip_path)

        if progress_cb:
            progress_cb(0.99, "正在解压模型…")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(target_dir)
        try:
            os.remove(zip_path)
        except Exception:
            pass

        if not os.path.exists(os.path.join(dest, "am", "final.mdl")):
            return False, "模型解压后不完整，请手动下载"
        return True, dest
    except Exception as e:
        return False, f"模型下载失败：{e}"
