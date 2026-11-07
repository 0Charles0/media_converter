"""转换引擎：图片使用 Pillow，音频 / 视频使用内置 FFmpeg。"""

from __future__ import annotations

import os
import re
import subprocess
import threading

from PIL import Image, ImageOps

import imageio_ffmpeg

from formats import Fmt

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)")
_PROGRESS_RE = re.compile(r"out_time_ms=(\d+)")


class ConvertError(Exception):
    pass


class ConvertCancelled(Exception):
    pass


def unique_path(path: str) -> str:
    """若目标已存在则自动追加 (1)、(2)... 避免覆盖。"""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    i = 1
    while True:
        cand = f"{stem} ({i}){ext}"
        if not os.path.exists(cand):
            return cand
        i += 1


def convert_file(src: str, out_dir: str, fmt: Fmt,
                 progress_cb, cancel_event: threading.Event) -> str:
    """转换单个文件，返回输出路径。progress_cb(0~1)。"""
    src = os.path.normpath(src)
    out_dir = os.path.normpath(out_dir)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(src))[0]
    dst = unique_path(os.path.join(out_dir, base + fmt.ext))

    if fmt.media == "image":
        _convert_image(src, dst, fmt)
        progress_cb(1.0)
    else:
        _convert_ffmpeg(src, dst, fmt, progress_cb, cancel_event)
    return dst


# ---------------------------------------------------------------- 图片
def _convert_image(src: str, dst: str, fmt: Fmt) -> None:
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    img.load()

    is_animated = getattr(img, "is_animated", False)
    if is_animated and fmt.pil_fmt in ("GIF", "WEBP"):
        frames, duration = _collect_frames(img)
        try:
            img.close()
            if fmt.pil_fmt == "GIF":
                frames = [f.convert("P") for f in frames]
            frames[0].save(
                dst, format=fmt.pil_fmt, save_all=True,
                append_images=frames[1:], duration=duration, loop=0,
            )
            return
        except Exception:
            frames[0].save(dst, format=fmt.pil_fmt)
            return

    pil = fmt.pil_fmt
    if pil == "JPEG":
        img = _flatten_to_rgb(img)
    elif pil == "XBM":
        img = img.convert("1")
    else:
        if img.mode == "P":
            img = img.convert("RGBA")
        elif img.mode not in ("RGB", "RGBA", "L", "1"):
            img = img.convert("RGB")
    img.save(dst, format=pil)


def _collect_frames(img: Image.Image) -> tuple[list[Image.Image], int]:
    frames = []
    try:
        img.seek(0)
        while True:
            frame = img.convert("RGBA")
            frames.append(frame.copy())
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    duration = img.info.get("duration", 100)
    return frames, duration


def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


# ---------------------------------------------------------------- FFmpeg
def _convert_ffmpeg(src: str, dst: str, fmt: Fmt,
                    progress_cb, cancel_event: threading.Event) -> None:
    cmd = [FFMPEG_EXE, "-y", "-hide_banner", "-nostats",
           "-progress", "pipe:1", "-i", src]

    if fmt.media == "audio":
        cmd += ["-vn", "-sn", "-dn"]
        if fmt.acodec:
            cmd += ["-c:a", fmt.acodec]
        if fmt.bitrate:
            cmd += ["-b:a", fmt.bitrate]
    else:
        if fmt.acodec:
            cmd += ["-c:a", fmt.acodec]
        if fmt.bitrate:
            cmd += ["-b:a", fmt.bitrate]
        if fmt.vcodec:
            cmd += ["-c:v", fmt.vcodec]
        if fmt.vcodec == "libx264":
            cmd += ["-pix_fmt", "yuv420p"]
        cmd += ["-sn", "-dn"]
        cmd += list(fmt.extra)

    cmd.append(dst)

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    total_sec: float | None = None
    last_error = ""
    line_iter = _iter_lines(proc.stdout)
    try:
        for line in line_iter:
            if cancel_event.is_set():
                proc.terminate()
                raise ConvertCancelled()
            m = _DURATION_RE.search(line)
            if m and total_sec is None:
                h, mi, s = m.groups()
                total_sec = int(h) * 3600 + int(mi) * 60 + float(s)
            pm = _PROGRESS_RE.search(line)
            if pm and total_sec:
                ms = int(pm.group(1)) / 1_000_000.0
                progress_cb(min(1.0, ms / total_sec))
            if "error" in line.lower():
                last_error = line.strip()
    finally:
        proc.stdout.close()

    ret = proc.wait()
    if ret != 0:
        raise ConvertError(last_error or f"FFmpeg 返回错误码 {ret}")
    progress_cb(1.0)


def _iter_lines(stream):
    while True:
        line = stream.readline()
        if not line:
            break
        yield line


# ---------------------------------------------------------------- 批量
def convert_batch(items, out_dir: str, fmt: Fmt,
                  progress_cb, status_cb, cancel_event: threading.Event):
    """转换批量文件。items: [(src, media), ...]
    progress_cb(overall 0~1, current_index, total)；status_cb(文本)。
    返回 (results, failures)，results 为 {src: dst}，failures 为 {src: 错误}。
    单个文件失败不影响其他文件继续转换。"""
    results: dict[str, str] = {}
    failures: dict[str, str] = {}
    total = len(items)
    done = 0
    for i, (src, media) in enumerate(items):
        if cancel_event.is_set():
            raise ConvertCancelled()
        if media != fmt.media:
            done += 1
            progress_cb(done / total, i, total, 1.0)
            continue

        def _cb(frac, _idx=i, _done=done):
            overall = (_done + frac) / total
            progress_cb(overall, _idx, total, frac)

        name = os.path.basename(src)
        status_cb(f"正在转换 {name}（{i + 1}/{total}）→ {fmt.key}")
        try:
            results[src] = convert_file(src, out_dir, fmt, _cb, cancel_event)
        except ConvertCancelled:
            raise
        except Exception as e:
            failures[src] = f"{type(e).__name__}: {e}"
        done += 1
        progress_cb(done / total, i, total, 1.0)
    return results, failures


def human_size(nbytes: int) -> str:
    size = float(nbytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"