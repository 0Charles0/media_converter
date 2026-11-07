"""生成应用图标 assets/app.ico 与预览图。运行：py build/make_icon.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw

SIZE = 256
COLOR_TOP = (43, 127, 255)     # 蓝
COLOR_BOTTOM = (168, 85, 247)  # 紫


def make_icon(size: int = SIZE) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 圆角矩形渐变背景
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=int(size * 0.22), fill=255)

    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        t = y / (size - 1)
        color = tuple(int(COLOR_TOP[i] + (COLOR_BOTTOM[i] - COLOR_TOP[i]) * t)
                      for i in range(3)) + (255,)
        d.line([(0, y), (size, y)], fill=color)
    bg.paste(img, mask=mask)
    img = bg

    # 白色 "转换" 箭头（左 ◀ 右 ▶）
    d = ImageDraw.Draw(img)
    s = size / 256.0
    tri_r = [(134 * s, 64 * s), (202 * s, 128 * s), (134 * s, 192 * s)]
    tri_l = [(122 * s, 64 * s), (54 * s, 128 * s), (122 * s, 192 * s)]
    d.polygon(tri_r, fill=(255, 255, 255, 255))
    d.polygon(tri_l, fill=(255, 255, 255, 200))

    return img


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets = os.path.join(root, "assets")
    os.makedirs(assets, exist_ok=True)

    img = make_icon()
    ico_path = os.path.join(assets, "app.ico")
    img.save(ico_path, format="ICO", sizes=[
        (16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
        (128, 128), (256, 256)])
    img.save(os.path.join(assets, "app_icon.png"), format="PNG")
    print("已生成:", ico_path)


if __name__ == "__main__":
    main()