"""媒体格式转换器 —— 简洁美观的图片 / 音频 / 视频格式转换工具。"""

import ctypes
import os
import queue
import sys
import threading

import customtkinter as ctk
from tkinterdnd2 import TkinterDnD

import core
from formats import FORMAT_BY_KEY, MEDIA_NAMES, detect_media_type

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

FONT = "Microsoft YaHei UI"

BADGE_COLORS = {"image": "#3B82F6", "audio": "#22C55E", "video": "#A855F7"}
GRAY = ("#666666", "#9AA0A6")
GREEN = "#16A34A"
RED = "#DC2626"
BG_PANEL = ("#F7F8FA", "#1F1F24")
CHIP_BG = ("#EEF0F2", "#2A2B30")
ACCENT = "#2B7FFF"


class MediaConverterApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("媒体格式转换器")
        self.geometry("1000x720")
        self.minsize(900, 660)

        self._font = ctk.CTkFont(family=FONT, size=13)
        self._font_small = ctk.CTkFont(family=FONT, size=12)
        self._font_title = ctk.CTkFont(family=FONT, size=20, weight="bold")

        self.files: list[dict] = []          # {path, media, name, size, status}
        self.selected_fmt_key: str | None = None
        self.out_dir: str = ""
        self._out_dir_auto = True
        self._q: queue.Queue = queue.Queue()
        self._cancel = threading.Event()
        self._running = False

        self._build_ui()
        self._bind_dnd()
        self._set_window_icon()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(60, self._poll)

    def _set_window_icon(self):
        try:
            if getattr(sys, "frozen", False):
                base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            else:
                base = os.path.dirname(os.path.abspath(__file__))
            icon = os.path.join(base, "assets", "app.ico")
            if os.path.exists(icon):
                self.iconbitmap(icon)
        except Exception:
            pass

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 顶栏
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 4))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="媒体格式转换器", font=self._font_title,
                     anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="图片 · 音频 · 视频 一键转换",
                     font=self._font_small, text_color=GRAY,
                     anchor="w").grid(row=1, column=0, sticky="w", pady=(2, 0))

        # 拖拽区
        drop = ctk.CTkFrame(self, fg_color=BG_PANEL, border_width=2,
                            border_color=ACCENT, corner_radius=16, height=112)
        drop.grid(row=1, column=0, sticky="ew", padx=24, pady=(12, 10))
        drop.grid_propagate(False)
        drop.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(drop, text="将文件拖拽到此处", font=ctk.CTkFont(
            family=FONT, size=16), anchor="center").grid(
            row=0, column=0, pady=(20, 2))
        ctk.CTkLabel(drop, text="支持常见图片、音频、视频文件",
                     font=self._font_small, text_color=GRAY).grid(
            row=1, column=0, pady=(0, 14))
        btns = ctk.CTkFrame(drop, fg_color="transparent")
        btns.grid(row=2, column=0, pady=(0, 18))
        ctk.CTkButton(btns, text="添加文件", width=120, height=34,
                      font=self._font, command=self._pick_files).pack(
            side="left", padx=6)
        ctk.CTkButton(btns, text="添加文件夹", width=120, height=34,
                      font=self._font, fg_color=CHIP_BG, text_color=("black", "white"),
                      hover_color=("#DDE0E4", "#3A3B41"), command=self._pick_folder).pack(
            side="left", padx=6)
        drop.bind("<Button-1>", lambda e: self._pick_files())
        for c in drop.winfo_children():
            c.bind("<Button-1>", lambda e: self._pick_files())

        # 主内容区
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 20))
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        self._build_file_list(main)
        self._build_options(main)

    def _build_file_list(self, parent):
        card = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=14)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 6))
        top.grid_columnconfigure(0, weight=1)
        self._list_title = ctk.CTkLabel(top, text="文件列表（0）",
                                        font=self._font, anchor="w")
        self._list_title.grid(row=0, column=0, sticky="w")
        self._clear_btn = ctk.CTkButton(
            top, text="清空", width=56, height=28, font=self._font_small,
            fg_color="transparent", text_color=GRAY, hover_color=CHIP_BG,
            command=self._clear_files, state="disabled")
        self._clear_btn.grid(row=0, column=1, sticky="e")

        self._list_frame = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self._list_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._list_frame.grid_columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self._list_frame, text="暂无文件\n添加文件后即可选择目标格式并转换",
            font=self._font_small, text_color=GRAY, justify="center")
        self._empty_label.grid(row=0, column=0, pady=48)

    def _build_options(self, parent):
        card = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=14)
        card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(card, text="目标格式", font=self._font,
                     anchor="w").grid(row=0, column=0, sticky="w", padx=18, pady=(16, 6))

        self._chip_frame = ctk.CTkScrollableFrame(
            card, fg_color="transparent", height=120)
        self._chip_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self._chip_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._fmt_hint = ctk.CTkLabel(card, text="请先添加文件", font=self._font_small,
                                      text_color=GRAY, anchor="w", wraplength=320)
        self._fmt_hint.grid(row=2, column=0, sticky="ew", padx=18, pady=(2, 10))

        ctk.CTkLabel(card, text="输出目录", font=self._font,
                     anchor="w").grid(row=3, column=0, sticky="w", padx=18, pady=(4, 6))

        dir_row = ctk.CTkFrame(card, fg_color="transparent")
        dir_row.grid(row=4, column=0, sticky="ew", padx=18)
        dir_row.grid_columnconfigure(0, weight=1)
        self._out_dir_var = ctk.StringVar(value="")
        self._dir_entry = ctk.CTkEntry(
            dir_row, height=36, font=self._font_small,
            textvariable=self._out_dir_var,
            placeholder_text="默认保存到源文件目录，可在此修改")
        self._dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._out_dir_var.trace_add("write", lambda *_: setattr(self, "_out_dir_auto", False))
        ctk.CTkButton(dir_row, text="浏览", width=68, height=36,
                      font=self._font_small, command=self._pick_out_dir).grid(
            row=0, column=1)

        self._convert_btn = ctk.CTkButton(
            card, text="开始转换", height=44, font=ctk.CTkFont(
                family=FONT, size=15, weight="bold"),
            fg_color=GREEN, hover_color="#138A3E", command=self._toggle_convert,
            state="disabled")
        self._convert_btn.grid(row=5, column=0, sticky="ew", padx=18, pady=(18, 8))

        self._progress = ctk.CTkProgressBar(card, height=10, corner_radius=5,
                                            progress_color=GREEN)
        self._progress.grid(row=6, column=0, sticky="ew", padx=18)
        self._progress.set(0)

        self._status = ctk.CTkLabel(card, text="就绪", font=self._font_small,
                                    text_color=GRAY, anchor="w", wraplength=340,
                                    justify="left")
        self._status.grid(row=7, column=0, sticky="ew", padx=18, pady=(8, 4))

        self._open_btn = ctk.CTkButton(
            card, text="打开输出目录", width=120, height=30, font=self._font_small,
            fg_color=CHIP_BG, text_color=("black", "white"),
            hover_color=("#DDE0E4", "#3A3B41"), command=self._open_out_dir,
            state="disabled")
        self._open_btn.grid(row=8, column=0, sticky="w", padx=18, pady=(2, 14))

    # ------------------------------------------------------------ 拖放
    def _bind_dnd(self):
        self.drop_target_register("DND_FILES")
        self.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        paths = self.tk.splitlist(event.data)
        self.add_files(list(paths))

    # ------------------------------------------------------------ 文件管理
    def add_files(self, paths: list[str]):
        added = 0
        for p in paths:
            p = os.path.normpath(p)
            if not os.path.isfile(p):
                continue
            media = detect_media_type(p)
            if media is None or any(f["path"] == p for f in self.files):
                continue
            self.files.append({
                "path": p, "media": media,
                "name": os.path.basename(p),
                "size": core.human_size(os.path.getsize(p)),
                "status": "pending",
            })
            added += 1
        if added:
            if self._out_dir_auto and not self._out_dir_var.get():
                self._out_dir_var.set(os.path.dirname(paths[0]))
            self._refresh_rows()
            self._refresh_chips()
        else:
            self._set_status("未添加文件：文件不存在或格式不受支持")

    def _remove_file(self, idx):
        self.files.pop(idx)
        self._refresh_rows()
        self._refresh_chips()

    def _clear_files(self):
        self.files.clear()
        self._refresh_rows()
        self._refresh_chips()

    def _refresh_rows(self):
        for c in self._list_frame.winfo_children():
            c.destroy()
        self._list_title.configure(text=f"文件列表（{len(self.files)}）")
        self._clear_btn.configure(state="normal" if self.files else "disabled")

        if not self.files:
            self._empty_label = ctk.CTkLabel(
                self._list_frame, text="暂无文件\n添加文件后即可选择目标格式并转换",
                font=self._font_small, text_color=GRAY, justify="center")
            self._empty_label.grid(row=0, column=0, pady=48)
            return

        for i, f in enumerate(self.files):
            self._add_row(i, f)

    def _add_row(self, i, f):
        row = ctk.CTkFrame(self._list_frame, fg_color="transparent")
        row.grid(row=i, column=0, sticky="ew", pady=2)
        row.grid_columnconfigure(1, weight=1)

        badge = ctk.CTkLabel(row, text=MEDIA_NAMES[f["media"]], width=46,
                             height=26, corner_radius=6,
                             fg_color=BADGE_COLORS[f["media"]], text_color="white",
                             font=self._font_small)
        badge.grid(row=0, column=0, padx=(0, 10), pady=(4, 0))

        ctk.CTkLabel(row, text=f["name"], font=self._font_small, anchor="w"
                     ).grid(row=0, column=1, sticky="ew", pady=(4, 0))
        ctk.CTkLabel(row, text=f["size"], font=self._font_small, text_color=GRAY,
                     anchor="e").grid(row=0, column=2, padx=10, pady=(4, 0))

        self._set_row_status(row, f["status"])

        ctk.CTkButton(row, text="移除", width=52, height=26, font=self._font_small,
                      fg_color="transparent", text_color=GRAY,
                      hover_color=CHIP_BG,
                      command=lambda idx=i: self._remove_file(idx)).grid(
            row=0, column=4, padx=(4, 0), pady=(4, 0))

        bar = ctk.CTkProgressBar(row, height=6, corner_radius=3, progress_color=GREEN)
        bar.grid(row=1, column=0, columnspan=5, sticky="ew", padx=(4, 8), pady=(2, 6))
        f["bar"] = bar
        if f["status"] == "done":
            bar.set(1.0)
        elif f["status"] == "failed":
            bar.set(1.0)
            bar.configure(progress_color=RED)
        else:
            bar.set(0)

    @staticmethod
    def _set_row_status(row, status):
        conf = {"pending": ("等待转换", GRAY),
                "done": ("已完成", GREEN),
                "failed": ("失败", RED),
                "skipped": ("已跳过", GRAY)}
        text, color = conf.get(status, ("", GRAY))
        lbl = ctk.CTkLabel(row, text=text, width=64, font=ctk.CTkFont(
            family=FONT, size=12), text_color=color, anchor="e")
        lbl.grid(row=0, column=3, padx=(0, 4))

    # ------------------------------------------------------------ 格式选择
    def _refresh_chips(self):
        for c in self._chip_frame.winfo_children():
            c.destroy()

        order = {"image": 0, "audio": 1, "video": 2}
        present = sorted({f["media"] for f in self.files}, key=order.get)
        if not present:
            self._fmt_hint.configure(text="请先添加文件")
            self._convert_btn.configure(state="disabled")
            return

        cur = FORMAT_BY_KEY.get(self.selected_fmt_key)
        if cur is None or cur.media not in present:
            self.selected_fmt_key = formats_for(present[0])[0].key

        row_i = 0
        col_i = 0
        for media in present:
            header = ctk.CTkLabel(
                self._chip_frame, text=f"{MEDIA_NAMES[media]}格式",
                font=self._font_small, text_color=GRAY, anchor="w")
            header.grid(row=row_i, column=0, columnspan=4, sticky="ew",
                        pady=(8 if row_i else 0, 4))
            row_i += 1
            for fmt in formats_for(media):
                btn = ctk.CTkButton(
                    self._chip_frame, text=fmt.key, height=32, corner_radius=8,
                    font=self._font_small,
                    fg_color=CHIP_BG, text_color=("black", "white"),
                    hover_color=("#DDE0E4", "#3A3B41"),
                    command=lambda k=fmt.key: self._select_fmt(k))
                btn.grid(row=row_i, column=col_i, sticky="ew", padx=4, pady=3)
                self._style_chip(btn, fmt.key == self.selected_fmt_key)
                col_i += 1
                if col_i == 4:
                    col_i = 0
                    row_i += 1
            if col_i != 0:
                row_i += 1
                col_i = 0

        self._update_fmt_hint()

    def _select_fmt(self, key):
        self.selected_fmt_key = key
        for c in self._chip_frame.winfo_children():
            if isinstance(c, ctk.CTkButton):
                self._style_chip(c, c.cget("text") == key)
        self._update_fmt_hint()

    @staticmethod
    def _style_chip(btn, selected):
        if selected:
            btn.configure(fg_color=ACCENT, text_color="white",
                          hover_color="#1F66E6")
        else:
            btn.configure(fg_color=CHIP_BG, text_color=("black", "white"),
                          hover_color=("#DDE0E4", "#3A3B41"))

    def _update_fmt_hint(self):
        fmt = FORMAT_BY_KEY.get(self.selected_fmt_key)
        if not fmt:
            self._fmt_hint.configure(text="请选择目标格式")
            self._convert_btn.configure(state="disabled")
            return
        n = sum(1 for f in self.files if f["media"] == fmt.media)
        self._fmt_hint.configure(text=f"将转换 {n} 个{fmt.label} → .{fmt.ext[1:]} 文件")
        self._convert_btn.configure(state="normal" if n else "disabled")

    # ------------------------------------------------------------ 转换
    def _toggle_convert(self):
        if self._running:
            self._cancel.set()
            self._set_status("正在取消…")
            return
        self._start_convert()

    def _start_convert(self):
        fmt = FORMAT_BY_KEY.get(self.selected_fmt_key)
        if not fmt:
            return
        items = [(f["path"], f["media"]) for f in self.files]
        out_dir = self._out_dir_var.get().strip()
        if not out_dir and items:
            out_dir = os.path.dirname(items[0][0])
            self._out_dir_var.set(out_dir)
        if not out_dir:
            self._set_status("请先选择输出目录", RED)
            return
        self.out_dir = out_dir
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError:
            self._set_status("输出目录无法创建，请检查路径", RED)
            return

        self._cancel.clear()
        self._running = True
        self._progress.set(0)
        for f in self.files:
            f["status"] = "pending"
        self._refresh_rows()
        self._set_running_state(True)
        self._set_status(f"准备转换 {len(items)} 个文件…")

        t = threading.Thread(target=self._worker, args=(items, out_dir, fmt),
                             daemon=True)
        t.start()

    def _worker(self, items, out_dir, fmt):
        try:
            results, failures = core.convert_batch(
                items, out_dir, fmt,
                lambda ov, i, t, f: self._q.put(("progress", ov, i, f)),
                lambda s: self._q.put(("status", s)),
                self._cancel)
            self._q.put(("done", results, failures))
        except core.ConvertCancelled:
            self._q.put(("cancelled",))
        except Exception as e:
            self._q.put(("error", str(e)))

    def _poll(self):
        try:
            while True:
                msg = self._q.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    _, overall, idx, frac = msg
                    self._progress.set(overall)
                    self._mark_row_progress(idx, frac)
                elif kind == "status":
                    self._set_status(msg[1])
                elif kind == "done":
                    self._on_done(*msg[1:])
                elif kind == "cancelled":
                    self._on_cancelled()
                elif kind == "error":
                    self._on_error(msg[1])
        except queue.Empty:
            pass
        if self._running:
            self.after(60, self._poll)
        else:
            self.after(200, self._poll)

    def _mark_row_progress(self, idx, frac):
        if 0 <= idx < len(self.files):
            bar = self.files[idx].get("bar")
            if bar:
                bar.set(frac)
            self._set_status(f"正在转换：{self.files[idx]['name']}")

    def _on_done(self, results, failures):
        self._running = False
        self._progress.set(1.0)
        ok = 0
        for f in self.files:
            if f["path"] in failures:
                f["status"] = "failed"
            elif f["path"] in results:
                f["status"] = "done"
                ok += 1
            else:
                f["status"] = "skipped"
        self._refresh_rows()
        self._set_running_state(False)
        total = len(self.files)
        if failures:
            self._set_status(
                f"完成 {ok}/{total}，{len(failures)} 个失败（详见文件列表）",
                RED if ok == 0 else None)
        else:
            self._set_status(f"全部完成：{ok} 个文件已转换到输出目录", GREEN)
        self._open_btn.configure(state="normal")

    def _on_cancelled(self):
        self._running = False
        for f in self.files:
            if f["status"] == "pending":
                f["status"] = "skipped"
        self._refresh_rows()
        self._set_running_state(False)
        self._set_status("已取消转换", GRAY)
        self._open_btn.configure(state="normal")

    def _on_error(self, err):
        self._running = False
        self._set_running_state(False)
        self._set_status(f"转换出错：{err}", RED)

    def _set_running_state(self, running):
        self._convert_btn.configure(
            text="取消转换" if running else "开始转换",
            fg_color=("#EF4444" if running else GREEN),
            hover_color=("#DC2626" if running else "#138A3E"))
        for w in (self._dir_entry, self._clear_btn):
            w.configure(state="disabled" if running else "normal")
        self._set_buttons_state(not running)

    def _set_buttons_state(self, enabled):
        for c in self._chip_frame.winfo_children():
            if isinstance(c, ctk.CTkButton):
                c.configure(state="normal" if enabled else "disabled")

    # ------------------------------------------------------------ 工具
    def _pick_files(self):
        if self._running:
            return
        paths = ctk.filedialog.askopenfilenames(
            title="选择要转换的文件",
            filetypes=[("媒体文件", "*.png *.jpg *.jpeg *.webp *.bmp *.gif "
                                "*.tif *.tiff *.ico *.tga *.avif *.mp3 *.wav "
                                "*.flac *.aac *.m4a *.ogg *.opus *.wma *.aiff "
                                "*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv "
                                "*.mpg *.mpeg *.m4v *.ts *.3gp *.ogv"),
                       ("所有文件", "*.*")])
        self.add_files(list(paths))

    def _pick_folder(self):
        if self._running:
            return
        d = ctk.filedialog.askdirectory(title="选择文件夹（转换其中的媒体文件）")
        if not d:
            return
        paths = []
        for root, _, names in os.walk(d):
            for n in names:
                p = os.path.join(root, n)
                if detect_media_type(p):
                    paths.append(p)
        self.add_files(paths)

    def _pick_out_dir(self):
        d = ctk.filedialog.askdirectory(
            title="选择输出目录", initialdir=self._out_dir_var.get() or self.out_dir)
        if d:
            self._out_dir_var.set(d)

    def _open_out_dir(self):
        try:
            os.startfile(self.out_dir)
        except OSError:
            pass

    def _set_status(self, text, color=None):
        self._status.configure(text=text, text_color=color or GRAY)

    def _on_close(self):
        self._cancel.set()
        self.destroy()


def formats_for(media: str):
    from formats import IMAGE_FORMATS, AUDIO_FORMATS, VIDEO_FORMATS
    return {"image": IMAGE_FORMATS, "audio": AUDIO_FORMATS,
            "video": VIDEO_FORMATS}[media]


if __name__ == "__main__":
    app = MediaConverterApp()
    app.mainloop()