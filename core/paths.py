# -*- coding: utf-8 -*-
"""路径工具：兼容「源码运行」与「PyInstaller 打包后运行」两种形态。"""
import os
import sys

from config import app_data_dir


def resource_path(rel):
    """返回打包后资源（如离线语音模型）所在路径。

    打包运行（onedir/onefile）时指向程序内置资源目录，与源码目录完全隔离；
    源码运行时返回项目根目录。
    """
    if getattr(sys, "frozen", False):
        # onefile：sys._MEIPASS 为运行时解压目录；onedir：为 exe 同级的 _internal 目录
        base = getattr(sys, "_MEIPASS", None)
        if base is None:
            base = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "_internal")
        return os.path.join(base, rel)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def vosk_model_path():
    """返回可用的 vosk 离线模型目录；找不到返回 None。

    查找顺序：1) 程序内置（EXE 内） 2) 用户数据目录（缓存/下载）。
    """
    candidates = [
        os.path.join(resource_path("models"), "vosk-model-small-cn-0.22"),
        os.path.join(app_data_dir(), "models", "vosk-model-small-cn-0.22"),
    ]
    for p in candidates:
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "am", "final.mdl")):
            return p
    return None


def vosk_model_download_dir():
    """离线模型下载目录（仅源码运行且模型缺失时用于下载）。"""
    return os.path.join(app_data_dir(), "models")
