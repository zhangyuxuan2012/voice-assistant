# -*- coding: utf-8 -*-
"""开发者工具：下载并解压 vosk 离线中文模型到 models/ 目录。

仅供【开发者打包】时使用一次；最终 EXE 已内置模型，用户无需执行本脚本。
"""
import os
import sys
import urllib.request
import zipfile

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip"
MODEL_DIR = "vosk-model-small-cn-0.22"


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest_dir = os.path.join(root, "models")
    dest = os.path.join(dest_dir, MODEL_DIR)

    if os.path.isdir(dest) and os.path.exists(os.path.join(dest, "am", "final.mdl")):
        print(f"[跳过] 模型已存在：{dest}")
        return 0

    os.makedirs(dest_dir, exist_ok=True)
    zip_path = os.path.join(dest_dir, MODEL_DIR + ".zip")
    print(f"[下载] {MODEL_URL}")
    req = urllib.request.Request(MODEL_URL, headers={"User-Agent": "VoiceAssistant-build"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(zip_path, "wb") as f:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r[下载] {done // 1024 // 1024}/{total // 1024 // 1024} MB", end="", flush=True)
    print()

    print(f"[解压] -> {dest_dir}")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest_dir)
    os.remove(zip_path)

    if not os.path.exists(os.path.join(dest, "am", "final.mdl")):
        print("[失败] 模型解压后不完整")
        return 1
    print("[完成] 离线模型已就绪")
    return 0


if __name__ == "__main__":
    sys.exit(main())
