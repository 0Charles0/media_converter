"""格式注册表：定义可用的图片 / 音频 / 视频格式及其转换参数。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Fmt:
    key: str                 # 唯一标识，如 "MP4"
    ext: str                 # 输出扩展名，如 ".mp4"
    media: str               # "image" | "audio" | "video"
    label: str               # 界面显示文本

    # FFmpeg 相关参数
    muxer: str | None = None   # 输出封装容器
    vcodec: str | None = None  # 视频编码器
    acodec: str | None = None  # 音频编码器
    bitrate: str | None = None # 音频码率
    extra: tuple = ()          # 附加参数

    # Pillow 相关参数
    pil_fmt: str | None = None # Pillow 保存格式名


# ---------------------------------------------------------------- 图片格式
def _img(key: str, ext: str, pil_fmt: str) -> Fmt:
    return Fmt(key=key, ext=ext, media="image", label=f"{key} 图片", pil_fmt=pil_fmt)


IMAGE_FORMATS: tuple[Fmt, ...] = (
    _img("PNG",  ".png",  "PNG"),
    _img("JPG",  ".jpg",  "JPEG"),
    _img("WEBP", ".webp", "WEBP"),
    _img("BMP",  ".bmp",  "BMP"),
    _img("GIF",  ".gif",  "GIF"),
    _img("TIFF", ".tiff", "TIFF"),
    _img("ICO",  ".ico",  "ICO"),
    _img("TGA",  ".tga",  "TGA"),
    _img("AVIF", ".avif", "AVIF"),
    _img("PDF",  ".pdf",  "PDF"),
    _img("QOI",  ".qoi",  "QOI"),
    _img("PCX",  ".pcx",  "PCX"),
    _img("ICNS", ".icns", "ICNS"),
    _img("XBM",  ".xbm",  "XBM"),
)

# ---------------------------------------------------------------- 音频格式
def _aud(key: str, ext: str, muxer: str, acodec: str, bitrate: str | None = None) -> Fmt:
    return Fmt(key=key, ext=ext, media="audio", label=f"{key} 音频",
               muxer=muxer, acodec=acodec, bitrate=bitrate)


AUDIO_FORMATS: tuple[Fmt, ...] = (
    _aud("MP3",   ".mp3",   "mp3",      "libmp3lame",   "192k"),
    _aud("WAV",   ".wav",   "wav",      "pcm_s16le"),
    _aud("FLAC",  ".flac",  "flac",     "flac"),
    _aud("AAC",   ".aac",   "adts",     "aac",          "192k"),
    _aud("M4A",   ".m4a",   "ipod",     "aac",          "192k"),
    _aud("OGG",   ".ogg",   "ogg",      "libvorbis",    "192k"),
    _aud("OPUS",  ".opus",  "opus",     "libopus",      "128k"),
    _aud("WMA",   ".wma",   "asf",      "wmav2",        "192k"),
    _aud("AIFF",  ".aiff",  "aiff",     "pcm_s16be"),
    _aud("AC3",   ".ac3",   "ac3",      "ac3",          "384k"),
    _aud("MKA",   ".mka",   "matroska", "libopus",      "128k"),
    _aud("MP2",   ".mp2",   "mp2",      "mp2",          "192k"),
    _aud("AMR",   ".amr",   "amr",      "libopencore_amrnb"),
    _aud("SPX",   ".spx",   "spx",      "libspeex",     "16k"),
    _aud("CAF",   ".caf",   "caf",      "aac",          "192k"),
)

# ---------------------------------------------------------------- 视频格式
def _vid(key: str, ext: str, muxer: str, vcodec: str,
         acodec: str = "aac", bitrate: str = "192k", extra: tuple = ()) -> Fmt:
    return Fmt(key=key, ext=ext, media="video", label=f"{key} 视频",
               muxer=muxer, vcodec=vcodec, acodec=acodec, bitrate=bitrate, extra=extra)


VIDEO_FORMATS: tuple[Fmt, ...] = (
    _vid("MP4",  ".mp4",  "mp4",     "libx264"),
    _vid("MKV",  ".mkv",  "matroska", "libx264"),
    _vid("AVI",  ".avi",  "avi",     "libx264"),
    _vid("MOV",  ".mov",  "mov",     "libx264"),
    _vid("WEBM", ".webm", "webm",    "libvpx-vp9", acodec="libopus", bitrate="128k",
         extra=("-crf", "33", "-b:v", "0", "-cpu-used", "4")),
    _vid("WMV",  ".wmv",  "asf",     "wmv2",   acodec="wmav2"),
    _vid("ASF",  ".asf",  "asf",     "wmv2",   acodec="wmav2"),
    _vid("FLV",  ".flv",  "flv",     "libx264"),
    _vid("MPEG", ".mpg",  "mpeg",    "mpeg2video", acodec="mp2", bitrate="192k"),
    _vid("VOB",  ".vob",  "mpeg",    "mpeg2video", acodec="ac3", bitrate="384k"),
    _vid("M4V",  ".m4v",  "m4v",     "mpeg4",  acodec="aac"),
    _vid("TS",   ".ts",   "mpegts",  "libx264"),
    _vid("M2TS", ".m2ts", "mpegts",  "libx264"),
    _vid("3GP",  ".3gp",  "3gp",     "libx264"),
    _vid("OGV",  ".ogv",  "ogv",     "libtheora", acodec="libvorbis", bitrate="128k"),
    _vid("GIF",  ".gif",  "gif",     "gif",    acodec=None, bitrate=None,
         extra=("-vf", "fps=15,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                "-loop", "0")),
)

ALL_FORMATS: tuple[Fmt, ...] = IMAGE_FORMATS + AUDIO_FORMATS + VIDEO_FORMATS
FORMAT_BY_KEY = {f.key: f for f in ALL_FORMATS}

MEDIA_NAMES = {"image": "图片", "audio": "音频", "video": "视频"}

# ---------------------------------------------------------------- 类型探测
IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp", ".gif", ".tif", ".tiff",
    ".ico", ".tga", ".avif", ".qoi", ".pcx", ".icns", ".xbm", ".dds", ".dib",
    ".sgi", ".ppm", ".pgm", ".pbm", ".psd", ".apng",
}
AUDIO_EXTS = {
    ".mp3", ".wav", ".flac", ".aac", ".m4a", ".m4b", ".ogg", ".oga", ".opus",
    ".wma", ".aiff", ".aif", ".ac3", ".eac3", ".mka", ".mp2", ".amr", ".awb",
    ".spx", ".caf", ".wv", ".ape", ".mid", ".midi",
}
VIDEO_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".asf", ".flv", ".mpg",
    ".mpeg", ".vob", ".m4v", ".ts", ".m2ts", ".mts", ".3gp", ".3g2", ".ogv",
    ".ogm", ".rm", ".rmvb", ".divx", ".dat", ".wtv", ".f4v", ".mp2v",
}

KNOWN_EXTS = IMAGE_EXTS | AUDIO_EXTS | VIDEO_EXTS


def detect_media_type(path: str) -> str | None:
    """根据扩展名判断媒体类型：image / audio / video / None。"""
    ext = _ext_of(path)
    if ext in IMAGE_EXTS:
        return "image"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    return None


def _ext_of(path: str) -> str:
    from os.path import splitext
    return splitext(path)[1].lower()


def input_formats_for(media: str) -> tuple[Fmt, ...]:
    """给定输入媒体类型，返回可选的输出格式。"""
    if media == "image":
        return IMAGE_FORMATS
    if media == "audio":
        return AUDIO_FORMATS
    if media == "video":
        return VIDEO_FORMATS
    return ()