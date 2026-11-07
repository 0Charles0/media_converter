"""截取应用界面用于 README。运行：py build/screenshot.py"""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageGrab
import imageio_ffmpeg as ifm
import subprocess

import app as appmod


def make_samples(d):
    from PIL import Image as PILImage
    PILImage.new("RGB", (1920, 1080), (32, 120, 220)).save(os.path.join(d, "风景照片.png"))
    PILImage.new("RGB", (800, 800), (240, 120, 60)).save(os.path.join(d, "作品集.jpg"))
    ff = ifm.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=10",
                    "-q:a", "2", os.path.join(d, "背景音乐.mp3")], capture_output=True)
    subprocess.run([ff, "-y", "-f", "lavfi", "-i", "testsrc=duration=10:size=1280x720:rate=30",
                    "-f", "lavfi", "-i", "sine=frequency=330:duration=10", "-shortest",
                    "-pix_fmt", "yuv420p", os.path.join(d, "宣传视频.mp4")], capture_output=True)


def main():
    d = tempfile.mkdtemp(prefix="mc_shot_")
    make_samples(d)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", "screenshot.png")

    a = appmod.MediaConverterApp()
    a.geometry("1080x760+120+80")
    a.add_files([os.path.join(d, n) for n in
                 ("风景照片.png", "作品集.jpg", "背景音乐.mp3", "宣传视频.mp4")])
    a._out_dir_var.set(os.path.join(d, "output"))
    a._select_fmt("JPG")
    a.attributes("-topmost", True)
    a.lift()
    a.update()
    time.sleep(1.0)
    a.update()

    x, y = a.winfo_rootx(), a.winfo_rooty()
    w, h = a.winfo_width(), a.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
    img.save(out)
    print("saved:", out, img.size)
    a.attributes("-topmost", False)
    a.destroy()


if __name__ == "__main__":
    main()