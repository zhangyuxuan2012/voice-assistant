# -*- coding: utf-8 -*-
"""开发者工具：生成应用图标 voice_assistant.ico（无需任何素材）。

用法：python make_icon.py
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def _gradient(size, top, bottom):
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    t = np.linspace(0.0, 1.0, size)[:, None, None]
    top = np.array(top, dtype=np.float32)
    bottom = np.array(bottom, dtype=np.float32)
    arr[:] = (top[None, None, :] + (bottom - top)[None, None, :] * t).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def build(size=512, radius=None):
    radius = radius or int(size * 0.22)
    img = _gradient(size, (37, 99, 235), (8, 145, 178))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1],
                                           radius=radius, fill=255)
    img.putalpha(mask)
    draw = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    s = size / 512.0

    # 话筒主体（胶囊形）
    draw.rounded_rectangle([int(x * s) for x in (196, 120, 316, 268)],
                           radius=int(52 * s), fill=white)
    # 话筒按钮（小圆点）
    draw.rounded_rectangle([int(x * s) for x in (238, 150, 274, 186)],
                           radius=int(12 * s), fill=(37, 99, 235, 255))
    # 支架（半圆弧）
    draw.arc([int(x * s) for x in (168, 200, 344, 376)],
             start=15, end=165, fill=white, width=int(24 * s))
    # 底部竖杆
    draw.line([int(256 * s), int(360 * s), int(256 * s), int(400 * s)],
              fill=white, width=int(24 * s))
    # 底座
    draw.rounded_rectangle([int(x * s) for x in (206, 388, 306, 414)],
                           radius=int(12 * s), fill=white)

    return img.filter(ImageFilter.SMOOTH_MORE)


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    img = build(512)
    ico_path = os.path.join(root, "voice_assistant.ico")
    img.save(ico_path, format="ICO",
             sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    img.save(os.path.join(root, "icon_preview.png"))
    print("OK:", ico_path)


if __name__ == "__main__":
    main()
