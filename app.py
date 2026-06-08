#!/usr/bin/env python3
"""
WaveDrop — Universal Media Downloader
Supports: YouTube, SoundCloud, Instagram, TikTok, and 1000+ sites
Requires: yt-dlp, customtkinter, ffmpeg
"""

import customtkinter as ctk
import threading
import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime

# ── Theme ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT       = "#6C63FF"
ACCENT_HOVER = "#574FD6"
BG_DARK      = "#0F0F14"
BG_CARD      = "#1A1A24"
BG_INPUT     = "#13131C"
BG_SIDEBAR   = "#121218"
TEXT_PRIMARY = "#EEEDF8"
TEXT_MUTED   = "#7A79A0"
TEXT_ACCENT  = "#A09FE0"
SUCCESS      = "#3ECFA0"
WARNING      = "#F5A623"
ERROR        = "#F05B5B"
BORDER       = "#2A2A3D"

DOWNLOAD_DIR = str(Path.home() / "Downloads" / "WaveDrop")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Ensure Homebrew bins are always on PATH
BREW_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
ENV = {**os.environ, "PATH": BREW_PATH + ":" + os.environ.get("PATH", "")}


def find_bin(name):
    """Find a binary by checking Homebrew paths then PATH."""
    for path in [f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}", f"/usr/bin/{name}"]:
        if os.path.exists(path):
            return path
    try:
        r = subprocess.run(["which", name], capture_output=True, text=True, env=ENV)
        found = r.stdout.strip()
        if found:
            return found
    except Exception:
        pass
    return name


def detect_platform(url):
    url_l = url.lower()
    if "youtube.com" in url_l or "youtu.be" in url_l:
        return "YouTube", "▶"
    if "soundcloud.com" in url_l:
        return "SoundCloud", "☁"
    if "instagram.com" in url_l:
        return "Instagram", "◈"
    if "tiktok.com" in url_l:
        return "TikTok", "♪"
    if "twitter.com" in url_l or "x.com" in url_l:
        return "X / Twitter", "✕"
    if "vimeo.com" in url_l:
        return "Vimeo", "○"
    return "Unknown Site", "◆"


# ── Download Job ──────────────────────────────────────────────────────────────
class DownloadJob:
    def __init__(self, url, mode, quality, fmt, status_cb, done_cb, progress_cb):
        self.url         = url.strip()
        self.mode        = mode
        self.quality     = quality
        self.fmt         = fmt
        self.status_cb   = status_cb
        self.done_cb     = done_cb
        self.progress_cb = progress_cb
        self.process     = None
        self.cancelled   = False

    def build_cmd(self):
        ytdlp  = find_bin("yt-dlp")
        ffmpeg = find_bin("ffmpeg")

        cmd = [ytdlp, "--newline", "--no-playlist", "--no-check-certificate"]
        cmd += ["--progress-template",
                "%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s"]
        cmd += ["--ffmpeg-location", ffmpeg]

        if self.mode == "audio":
            cmd += ["-x"]
            aformat = self.fmt if self.fmt in ("mp3", "m4a", "wav", "flac", "opus") else "mp3"
            cmd += ["--audio-format", aformat]
            if self.quality in ("320", "192", "128"):
                cmd += ["--audio-quality", "0" if self.quality == "320" else self.quality + "k"]
            else:
                cmd += ["--audio-quality", "0"]
        else:
            if self.quality == "1080":
                vfmt = "bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=1080]"
            elif self.quality == "720":
                vfmt = "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720]"
            elif self.quality == "480":
                vfmt = "bestvideo[height<=480][ext=mp4]+bestaudio/best[height<=480]"
            else:
                vfmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            cmd += ["-f", vfmt]
            cmd += ["--merge-output-format",
                    self.fmt if self.fmt in ("mp4", "webm", "mkv") else "mp4"]

        cmd += ["-o", os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")]
        cmd += [self.url]
        return cmd

    def run(self):
        try:
            cmd = self.build_cmd()
            self.status_cb(f"⬇ Starting… (yt-dlp: {cmd[0]})", TEXT_ACCENT)
            last_lines = []

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=ENV
            )

            for line in self.process.stdout:
                if self.cancelled:
                    break
                line = line.strip()
                if not line:
                    continue
                last_lines.append(line)
                if len(last_lines) > 8:
                    last_lines.pop(0)

                if "|" in line and "%" in line:
                    parts = line.split("|")
                    pct_str = parts[0].strip().replace("%", "").strip()
                    speed   = parts[1].strip() if len(parts) > 1 else ""
                    eta     = parts[2].strip() if len(parts) > 2 else ""
                    try:
                        pct = float(pct_str)
                        self.progress_cb(pct, speed, eta)
                    except ValueError:
                        pass
                elif any(k in line for k in ("[download]", "[ExtractAudio]", "[ffmpeg]", "[Merger]")):
                    self.status_cb(line[:90], TEXT_MUTED)
                elif "ERROR" in line.upper():
                    self.status_cb(line[:90], ERROR)

            self.process.wait()
            if self.cancelled:
                self.done_cb(False, "Cancelled.")
            elif self.process.returncode == 0:
                self.done_cb(True, "Download complete!")
            else:
                # Show the most useful error line
                err = next((l for l in reversed(last_lines) if "ERROR" in l.upper()), None)
                if not err:
                    err = last_lines[-1] if last_lines else "Unknown error"
                self.done_cb(False, err[:120])
        except FileNotFoundError as e:
            self.done_cb(False, f"Not found: {e}. Run setup.sh first.")
        except Exception as e:
            self.done_cb(False, str(e))

    def cancel(self):
        self.cancelled = True
        if self.process:
            self.process.terminate()


# ── History Row ───────────────────────────────────────────────────────────────
class HistoryRow(ctk.CTkFrame):
    def __init__(self, parent, title, platform, mode, fmt, timestamp, **kw):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=8, **kw)
        self.configure(border_width=1, border_color=BORDER)

        icon_map = {"YouTube": "▶", "SoundCloud": "☁", "Instagram": "◈",
                    "TikTok": "♪", "X / Twitter": "✕", "Vimeo": "○"}
        icon  = icon_map.get(platform, "◆")
        color = SUCCESS if mode == "audio" else TEXT_ACCENT

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=12, pady=8)

        top = ctk.CTkFrame(left, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=f"{icon} {platform}",
                     font=("SF Pro Display", 11), text_color=color).pack(side="left")
        ctk.CTkLabel(top, text=fmt.upper(),
                     font=("SF Pro Display", 10), text_color=TEXT_MUTED).pack(side="right")

        ctk.CTkLabel(left, text=title[:60] + ("…" if len(title) > 60 else ""),
                     font=("SF Pro Display", 12, "bold"), text_color=TEXT_PRIMARY,
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(left, text=timestamp,
                     font=("SF Pro Display", 10), text_color=TEXT_MUTED,
                     anchor="w").pack(fill="x")


# ── Main App ──────────────────────────────────────────────────────────────────
class WaveDropApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WaveDrop")
        self.geometry("860x620")
        self.minsize(760, 540)
        self.configure(fg_color=BG_DARK)
        self.resizable(True, True)
        self._job = None
        self._history = []
        self._pending_history = {}
        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.sidebar = ctk.CTkFrame(self, width=200, fg_color=BG_SIDEBAR, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo_f = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_f.pack(padx=20, pady=(28, 20), fill="x")
        ctk.CTkLabel(logo_f, text="◉ WaveDrop",
                     font=("SF Pro Display", 18, "bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(logo_f, text="Universal Downloader",
                     font=("SF Pro Display", 10), text_color=TEXT_MUTED).pack(anchor="w")

        self._nav_dl  = self._sidebar_btn("⬇  Download", self._show_download, active=True)
        self._nav_his = self._sidebar_btn("◷  History",  self._show_history)
        self._nav_set = self._sidebar_btn("⚙  Settings", self._show_settings)

        ctk.CTkLabel(self.sidebar, text="Supports 1000+ sites\nvia yt-dlp",
                     font=("SF Pro Display", 10), text_color=TEXT_MUTED,
                     justify="left").pack(side="bottom", padx=20, pady=20, anchor="w")

        self.content = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

        self.page_dl  = ctk.CTkFrame(self.content, fg_color="transparent")
        self.page_his = ctk.CTkFrame(self.content, fg_color="transparent")
        self.page_set = ctk.CTkFrame(self.content, fg_color="transparent")

        self._build_download_page()
        self._build_history_page()
        self._build_settings_page()
        self._show_download()

    def _sidebar_btn(self, text, cmd, active=False):
        btn = ctk.CTkButton(
            self.sidebar, text=text, command=cmd,
            fg_color=ACCENT if active else "transparent",
            hover_color=ACCENT_HOVER,
            text_color=TEXT_PRIMARY if active else TEXT_MUTED,
            font=("SF Pro Display", 13), anchor="w",
            height=40, corner_radius=8
        )
        btn.pack(padx=12, pady=3, fill="x")
        return btn

    def _activate_nav(self, active):
        for btn in [self._nav_dl, self._nav_his, self._nav_set]:
            btn.configure(fg_color="transparent", text_color=TEXT_MUTED)
        active.configure(fg_color=ACCENT, text_color=TEXT_PRIMARY)

    def _show_download(self):
        self._activate_nav(self._nav_dl)
        self.page_his.pack_forget()
        self.page_set.pack_forget()
        self.page_dl.pack(fill="both", expand=True)

    def _show_history(self):
        self._activate_nav(self._nav_his)
        self.page_dl.pack_forget()
        self.page_set.pack_forget()
        self._refresh_history()
        self.page_his.pack(fill="both", expand=True)

    def _show_settings(self):
        self._activate_nav(self._nav_set)
        self.page_dl.pack_forget()
        self.page_his.pack_forget()
        self.page_set.pack(fill="both", expand=True)

    # ── Download Page ─────────────────────────────────────────────────────────
    def _build_download_page(self):
        p = self.page_dl
        PX = 32

        ctk.CTkLabel(p, text="Download Media",
                     font=("SF Pro Display", 22, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=PX, pady=(30, 4))
        ctk.CTkLabel(p, text="Paste any link — YouTube, SoundCloud, TikTok, Instagram, and more",
                     font=("SF Pro Display", 13), text_color=TEXT_MUTED).pack(anchor="w", padx=PX, pady=(0, 20))

        # URL card
        url_card = ctk.CTkFrame(p, fg_color=BG_CARD, corner_radius=12,
                                border_width=1, border_color=BORDER)
        url_card.pack(fill="x", padx=PX, pady=(0, 16))

        ctk.CTkLabel(url_card, text="URL", font=("SF Pro Display", 11),
                     text_color=TEXT_MUTED).pack(anchor="w", padx=16, pady=(14, 4))

        url_row = ctk.CTkFrame(url_card, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(0, 6))

        self.url_entry = ctk.CTkEntry(
            url_row, placeholder_text="https://…",
            font=("SF Pro Mono", 13), height=42,
            fg_color=BG_INPUT, border_color=BORDER, border_width=1,
            text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda _: self._start_download())

        ctk.CTkButton(url_row, text="Paste", width=70, height=42,
                      fg_color=BG_INPUT, hover_color=BORDER, text_color=TEXT_MUTED,
                      border_width=1, border_color=BORDER,
                      font=("SF Pro Display", 12), command=self._paste_url).pack(side="left")

        self.platform_label = ctk.CTkLabel(url_card, text="",
                                           font=("SF Pro Display", 11), text_color=TEXT_ACCENT)
        self.platform_label.pack(anchor="w", padx=16, pady=(0, 10))
        self.url_entry.bind("<KeyRelease>", self._on_url_change)

        # Options card
        opts_card = ctk.CTkFrame(p, fg_color=BG_CARD, corner_radius=12,
                                 border_width=1, border_color=BORDER)
        opts_card.pack(fill="x", padx=PX, pady=(0, 16))

        opts_inner = ctk.CTkFrame(opts_card, fg_color="transparent")
        opts_inner.pack(fill="x", padx=16, pady=14)

        # Format
        mode_col = ctk.CTkFrame(opts_inner, fg_color="transparent")
        mode_col.pack(side="left", expand=True, fill="x")
        ctk.CTkLabel(mode_col, text="FORMAT", font=("SF Pro Display", 10, "bold"),
                     text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 6))
        self.mode_var = ctk.StringVar(value="audio")
        ctk.CTkSegmentedButton(
            mode_col, values=["audio", "video"], variable=self.mode_var,
            command=self._on_mode_change,
            fg_color=BG_INPUT, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            unselected_color=BG_INPUT, unselected_hover_color=BORDER,
            text_color=TEXT_PRIMARY, font=("SF Pro Display", 12), height=38
        ).pack(fill="x")

        # Quality
        qual_col = ctk.CTkFrame(opts_inner, fg_color="transparent")
        qual_col.pack(side="left", expand=True, fill="x", padx=(20, 0))
        ctk.CTkLabel(qual_col, text="QUALITY", font=("SF Pro Display", 10, "bold"),
                     text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 6))
        self.quality_var = ctk.StringVar(value="best")
        self.quality_menu = ctk.CTkOptionMenu(
            qual_col, values=["best", "320kbps", "192kbps", "128kbps"],
            variable=self.quality_var,
            fg_color=BG_INPUT, button_color=BG_INPUT, button_hover_color=BORDER,
            text_color=TEXT_PRIMARY, dropdown_fg_color=BG_CARD,
            dropdown_text_color=TEXT_PRIMARY, font=("SF Pro Display", 12), height=38
        )
        self.quality_menu.pack(fill="x")

        # File type
        fmt_col = ctk.CTkFrame(opts_inner, fg_color="transparent")
        fmt_col.pack(side="left", expand=True, fill="x", padx=(20, 0))
        ctk.CTkLabel(fmt_col, text="FILE TYPE", font=("SF Pro Display", 10, "bold"),
                     text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 6))
        self.fmt_var = ctk.StringVar(value="mp3")
        self.fmt_menu = ctk.CTkOptionMenu(
            fmt_col, values=["mp3", "m4a", "wav", "flac"],
            variable=self.fmt_var,
            fg_color=BG_INPUT, button_color=BG_INPUT, button_hover_color=BORDER,
            text_color=TEXT_PRIMARY, dropdown_fg_color=BG_CARD,
            dropdown_text_color=TEXT_PRIMARY, font=("SF Pro Display", 12), height=38
        )
        self.fmt_menu.pack(fill="x")

        # Download button
        self.dl_btn = ctk.CTkButton(
            p, text="⬇  Download", command=self._start_download,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=("SF Pro Display", 14, "bold"),
            height=50, corner_radius=12, text_color="white"
        )
        self.dl_btn.pack(fill="x", padx=PX, pady=(0, 16))

        # Progress card
        prog_card = ctk.CTkFrame(p, fg_color=BG_CARD, corner_radius=12,
                                 border_width=1, border_color=BORDER)
        prog_card.pack(fill="x", padx=PX, pady=(0, 0))

        prog_inner = ctk.CTkFrame(prog_card, fg_color="transparent")
        prog_inner.pack(fill="x", padx=16, pady=14)

        self.status_label = ctk.CTkLabel(prog_inner, text="Ready",
                                         font=("SF Pro Display", 12), text_color=TEXT_MUTED,
                                         anchor="w", wraplength=700)
        self.status_label.pack(fill="x")

        self.progress_bar = ctk.CTkProgressBar(prog_inner, height=6,
                                               progress_color=ACCENT, fg_color=BG_INPUT,
                                               corner_radius=3)
        self.progress_bar.pack(fill="x", pady=(8, 6))
        self.progress_bar.set(0)

        meta_row = ctk.CTkFrame(prog_inner, fg_color="transparent")
        meta_row.pack(fill="x")
        self.speed_label = ctk.CTkLabel(meta_row, text="",
                                        font=("SF Pro Display", 11), text_color=TEXT_MUTED, anchor="w")
        self.speed_label.pack(side="left")
        self.eta_label = ctk.CTkLabel(meta_row, text="",
                                      font=("SF Pro Display", 11), text_color=TEXT_MUTED, anchor="e")
        self.eta_label.pack(side="right")

        btn_row = ctk.CTkFrame(prog_inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(btn_row, text="Open Downloads Folder", command=self._open_folder,
                      fg_color="transparent", hover_color=BORDER, text_color=TEXT_ACCENT,
                      border_width=1, border_color=BORDER,
                      font=("SF Pro Display", 12), height=36, corner_radius=8).pack(side="left")
        self.cancel_btn = ctk.CTkButton(btn_row, text="Cancel", command=self._cancel_download,
                                        fg_color="transparent", hover_color=BORDER,
                                        text_color=ERROR, border_width=1, border_color=BORDER,
                                        font=("SF Pro Display", 12), height=36, corner_radius=8)
        self.cancel_btn.pack(side="right")
        self.cancel_btn.configure(state="disabled")

    def _on_url_change(self, event=None):
        url = self.url_entry.get().strip()
        if url:
            name, icon = detect_platform(url)
            self.platform_label.configure(text=f"{icon} {name} detected")
        else:
            self.platform_label.configure(text="")

    def _on_mode_change(self, val):
        if val == "audio":
            self.quality_menu.configure(values=["best", "320kbps", "192kbps", "128kbps"])
            self.quality_var.set("best")
            self.fmt_menu.configure(values=["mp3", "m4a", "wav", "flac"])
            self.fmt_var.set("mp3")
        else:
            self.quality_menu.configure(values=["best", "1080p", "720p", "480p"])
            self.quality_var.set("best")
            self.fmt_menu.configure(values=["mp4", "webm", "mkv"])
            self.fmt_var.set("mp4")

    def _paste_url(self):
        try:
            text = self.clipboard_get()
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, text)
            self._on_url_change()
        except Exception:
            pass

    def _start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self._set_status("Please enter a URL first.", ERROR)
            return
        if self._job is not None:
            self._set_status("A download is already in progress.", WARNING)
            return

        mode    = self.mode_var.get()
        quality = self.quality_var.get().replace("kbps", "").replace("p", "")
        fmt     = self.fmt_var.get()

        self.progress_bar.set(0)
        self.speed_label.configure(text="")
        self.eta_label.configure(text="")
        self.dl_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")

        platform, _ = detect_platform(url)
        self._pending_history = {
            "url": url, "platform": platform, "mode": mode, "fmt": fmt
        }

        self._job = DownloadJob(
            url, mode, quality, fmt,
            status_cb=self._set_status,
            done_cb=self._on_done,
            progress_cb=self._on_progress
        )
        threading.Thread(target=self._job.run, daemon=True).start()

    def _cancel_download(self):
        if self._job:
            self._job.cancel()

    def _set_status(self, msg, color=TEXT_MUTED):
        self.after(0, lambda: self.status_label.configure(text=msg, text_color=color))

    def _on_progress(self, pct, speed, eta):
        def _u():
            self.progress_bar.set(pct / 100)
            self.speed_label.configure(text=f"⚡ {speed}")
            self.eta_label.configure(text=f"ETA {eta}")
        self.after(0, _u)

    def _on_done(self, success, msg):
        def _u():
            self._job = None
            self.dl_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")
            if success:
                self.progress_bar.set(1)
                self._set_status("✓ " + msg, SUCCESS)
                if self._pending_history:
                    h = self._pending_history
                    self._history.insert(0, {
                        "title": h["url"].split("?")[0][-60:],
                        "platform": h["platform"],
                        "mode": h["mode"],
                        "fmt": h["fmt"],
                        "timestamp": datetime.now().strftime("%b %d, %Y  %H:%M")
                    })
            else:
                self._set_status("✗ " + msg, ERROR)
        self.after(0, _u)

    def _open_folder(self):
        subprocess.Popen(["open", DOWNLOAD_DIR])

    # ── History Page ──────────────────────────────────────────────────────────
    def _build_history_page(self):
        p = self.page_his
        ctk.CTkLabel(p, text="Download History",
                     font=("SF Pro Display", 22, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=32, pady=(30, 4))
        ctk.CTkLabel(p, text="Recent downloads this session",
                     font=("SF Pro Display", 13), text_color=TEXT_MUTED).pack(anchor="w", padx=32, pady=(0, 20))
        self.history_scroll = ctk.CTkScrollableFrame(
            p, fg_color="transparent",
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=ACCENT)
        self.history_scroll.pack(fill="both", expand=True, padx=32, pady=(0, 20))

    def _refresh_history(self):
        for w in self.history_scroll.winfo_children():
            w.destroy()
        if not self._history:
            ctk.CTkLabel(self.history_scroll, text="No downloads yet this session.",
                         font=("SF Pro Display", 14), text_color=TEXT_MUTED).pack(pady=40)
            return
        for h in self._history:
            HistoryRow(self.history_scroll,
                       title=h["title"], platform=h["platform"],
                       mode=h["mode"], fmt=h["fmt"],
                       timestamp=h["timestamp"]).pack(fill="x", pady=4)

    # ── Settings Page ─────────────────────────────────────────────────────────
    def _build_settings_page(self):
        p = self.page_set
        PX = 32

        ctk.CTkLabel(p, text="Settings",
                     font=("SF Pro Display", 22, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=PX, pady=(30, 4))
        ctk.CTkLabel(p, text="Configure WaveDrop",
                     font=("SF Pro Display", 13), text_color=TEXT_MUTED).pack(anchor="w", padx=PX, pady=(0, 20))

        card = ctk.CTkFrame(p, fg_color=BG_CARD, corner_radius=12,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=PX, pady=(0, 16))

        # Download folder row
        r = ctk.CTkFrame(card, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(r, text="Download folder", font=("SF Pro Display", 13),
                     text_color=TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(r, text=DOWNLOAD_DIR, font=("SF Pro Mono", 11),
                     text_color=TEXT_MUTED).pack(side="right")

        # Theme row
        r2 = ctk.CTkFrame(card, fg_color="transparent")
        r2.pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(r2, text="Appearance", font=("SF Pro Display", 13),
                     text_color=TEXT_PRIMARY).pack(side="left")
        theme_var = ctk.StringVar(value="dark")
        ctk.CTkOptionMenu(r2, values=["dark", "light", "system"],
                          variable=theme_var,
                          command=lambda v: ctk.set_appearance_mode(v),
                          fg_color=BG_INPUT, button_color=BG_INPUT,
                          button_hover_color=BORDER, text_color=TEXT_PRIMARY,
                          dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
                          font=("SF Pro Display", 12), width=120).pack(side="right")

        # Dependency status
        dep_card = ctk.CTkFrame(p, fg_color=BG_CARD, corner_radius=12,
                                border_width=1, border_color=BORDER)
        dep_card.pack(fill="x", padx=PX)

        ctk.CTkLabel(dep_card, text="DEPENDENCIES",
                     font=("SF Pro Display", 10, "bold"), text_color=TEXT_MUTED).pack(
            anchor="w", padx=16, pady=(14, 6))

        for name in ["yt-dlp", "ffmpeg"]:
            found = find_bin(name)
            ok = os.path.exists(found) or found == name
            # Actually test it
            try:
                subprocess.run([found, "--version"], capture_output=True, timeout=3)
                ok = True
                display = found
            except Exception:
                ok = False
                display = "not found"

            dr = ctk.CTkFrame(dep_card, fg_color="transparent")
            dr.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(dr, text=name, font=("SF Pro Display", 13),
                         text_color=TEXT_PRIMARY).pack(side="left")
            ctk.CTkLabel(dr, text=f"✓ {display}" if ok else "✗ Not found",
                         font=("SF Pro Display", 11),
                         text_color=SUCCESS if ok else ERROR).pack(side="right")

        ctk.CTkFrame(dep_card, fg_color="transparent", height=10).pack()


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = WaveDropApp()
    app.mainloop()
