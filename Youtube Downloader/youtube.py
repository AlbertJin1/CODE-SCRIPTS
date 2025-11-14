# youtube.py
import os
import re
import sys
import threading
import customtkinter as ctk
import yt_dlp
import requests
import tarfile
import shutil
import tempfile
from tkinter import filedialog, messagebox
from PIL import Image
from io import BytesIO
import tkinter as tk
import time
from typing import Optional

# ------------------------------------------------------------------
# App Info
# ------------------------------------------------------------------
APP_NAME = "Video Downloader Plus"
APP_VERSION = "0.1.0"
APP_AUTHOR = "Jessie Albert J. Regualos"
APP_YEAR = "2025"

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
ICONS_DIR = os.path.join(BASE_DIR, "icons")
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg.exe")
os.makedirs(ICONS_DIR, exist_ok=True)

APP_ICON_PATH = os.path.join(ICONS_DIR, "download_arrow.png")
INFO_ICON_PATH = os.path.join(ICONS_DIR, "info.png")
PROFILE_ICON_PATH = os.path.join(ICONS_DIR, "profile.png")
FAQ_ICON_PATH = os.path.join(ICONS_DIR, "faq.png")

_REMOTE_URLS = {
    APP_ICON_PATH: "https://cdn-icons-png.flaticon.com/512/2989/2989988.png",
    INFO_ICON_PATH: "https://cdn-icons-png.flaticon.com/512/189/189664.png",
    PROFILE_ICON_PATH: "https://cdn-icons-png.flaticon.com/512/4140/4140048.png",
    FAQ_ICON_PATH: "https://cdn-icons-png.flaticon.com/512/189/189665.png",
}


# ------------------------------------------------------------------
# 1. Ensure Icons
# ------------------------------------------------------------------
def ensure_icons():
    for local_path, url in _REMOTE_URLS.items():
        if os.path.exists(local_path):
            continue
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(r.content)
        except Exception:
            pass


threading.Thread(target=ensure_icons, daemon=True).start()


# ------------------------------------------------------------------
# 2. Auto-Update yt-dlp (frozen only)
# ------------------------------------------------------------------
def update_yt_dlp():
    if not getattr(sys, "frozen", False):
        return
    try:
        current = yt_dlp.version.__version__
        resp = requests.get("https://pypi.org/pypi/yt-dlp/json", timeout=10)
        latest = resp.json()["info"]["version"]
        if latest == current:
            return

        url = f"https://files.pythonhosted.org/packages/source/y/yt-dlp/yt-dlp-{latest}.tar.gz"
        r = requests.get(url, stream=True, timeout=15)
        r.raise_for_status()

        with tempfile.TemporaryDirectory() as tmp:
            tar_path = os.path.join(tmp, f"yt-dlp-{latest}.tar.gz")
            with open(tar_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)

            extract_dir = os.path.join(tmp, "extract")
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(extract_dir)

            pkg_dir = next(
                (
                    os.path.join(root, "yt_dlp")
                    for root, dirs, _ in os.walk(extract_dir)
                    if "yt_dlp" in dirs
                ),
                None,
            )
            if not pkg_dir:
                return

            target_dir = os.path.join(sys._MEIPASS, "yt_dlp")
            backup_dir = target_dir + "_backup"
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            if os.path.exists(target_dir):
                shutil.move(target_dir, backup_dir)
            shutil.copytree(pkg_dir, target_dir)

        messagebox.showinfo("Update", f"yt-dlp updated to {latest}\nRestarting...")
        os.execv(sys.executable, ["python"] + sys.argv)
    except Exception:
        pass


threading.Thread(target=update_yt_dlp, daemon=True).start()


# ------------------------------------------------------------------
# 3. Image Loaders
# ------------------------------------------------------------------
def load_ctk_image(local_path: str, size: tuple) -> Optional[ctk.CTkImage]:
    try:
        img = Image.open(local_path).convert("RGBA")
        img = img.resize(size, Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img)
    except Exception:
        return None


def load_photo_image(local_path: str) -> Optional[tk.PhotoImage]:
    try:
        return tk.PhotoImage(file=local_path)
    except Exception:
        return None


# ------------------------------------------------------------------
# 4. Main App
# ------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class YouTubeDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("720x650")
        self.resizable(False, False)

        # Icons
        self.app_icon_ctk = load_ctk_image(APP_ICON_PATH, (64, 64))
        self.app_icon_tk = load_photo_image(APP_ICON_PATH)
        self.info_icon = load_ctk_image(INFO_ICON_PATH, (18, 18))
        self.profile_icon = load_ctk_image(PROFILE_ICON_PATH, (80, 80))
        self.faq_icon = load_ctk_image(FAQ_ICON_PATH, (18, 18))

        if self.app_icon_tk:
            self.iconphoto(True, self.app_icon_tk)

        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.format_var = ctk.StringVar(
            value="bestvideo+bestaudio/best"
        )  # Original best quality
        self.subs_var = ctk.BooleanVar()
        self.cancel_event = threading.Event()
        self.current_thread = None

        self.create_widgets()

    def create_widgets(self):
        # Header
        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text=APP_NAME, font=ctk.CTkFont(size=24, weight="bold")
        ).pack(side="left", padx=(10, 0))
        ctk.CTkLabel(
            header, text=f"v{APP_VERSION}", font=ctk.CTkFont(size=12), text_color="#888"
        ).pack(side="left", padx=(5, 20))

        ctk.CTkButton(
            header,
            text=" FAQ",
            image=self.faq_icon,
            compound="left",
            width=100,
            command=self.show_faq,
            fg_color="transparent",
            border_width=1,
            border_color="#555",
        ).pack(side="right")
        ctk.CTkButton(
            header,
            text=" About",
            image=self.info_icon,
            compound="left",
            width=100,
            command=self.show_about,
            fg_color="transparent",
            border_width=1,
            border_color="#555",
        ).pack(side="right", padx=(0, 5))

        # URL
        url_frame = ctk.CTkFrame(self)
        url_frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(url_frame, text="URL:", font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=10, pady=(10, 2)
        )
        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="https://youtube.com/watch?v=...",
            font=ctk.CTkFont(size=12),
        )
        self.url_entry.pack(fill="x", padx=10, pady=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self.start_download())

        # Save Path
        path_frame = ctk.CTkFrame(self)
        path_frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(path_frame, text="Save to:", font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=10, pady=(10, 2)
        )
        path_inner = ctk.CTkFrame(path_frame)
        path_inner.pack(fill="x", padx=10, pady=(0, 10))
        self.path_label = ctk.CTkLabel(
            path_inner, text=self.download_path, anchor="w", font=ctk.CTkFont(size=11)
        )
        self.path_label.pack(side="left", fill="x", expand=True, padx=(5, 0))
        ctk.CTkButton(
            path_inner, text="Browse", width=80, command=self.browse_folder
        ).pack(side="right")

        # Format
        format_frame = ctk.CTkFrame(self)
        format_frame.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(format_frame, text="Format:", font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=10, pady=(10, 2)
        )
        formats = [
            ("Best Quality (Video + Audio)", "bestvideo+bestaudio/best"),  # ORIGINAL
            (
                "MP4 1080p",
                "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]",
            ),
            (
                "MP4 720p",
                "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]",
            ),
            (
                "MP4 480p",
                "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/best[ext=mp4][height<=480]",
            ),
            ("Audio Only (MP3)", "bestaudio/best"),
            ("Worst Quality", "worst[ext=mp4]/worst"),
        ]
        for text, val in formats:
            ctk.CTkRadioButton(
                format_frame, text=text, variable=self.format_var, value=val
            ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkCheckBox(
            self, text="Download Subtitles (if available)", variable=self.subs_var
        ).pack(anchor="w", padx=20, pady=(5, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=15, padx=20, fill="x")
        self.download_btn = ctk.CTkButton(
            btn_frame,
            text="Download",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#FF0000",
            hover_color="#CC0000",
            command=self.start_download,
        )
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#666",
            hover_color="#555",
            command=self.cancel_download,
            state="disabled",
        )
        self.cancel_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # Progress
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(pady=(0, 5), padx=20, fill="x")
        self.progress.set(0)
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready.",
            text_color="#AAA",
            font=ctk.CTkFont(size=11),
            anchor="center",
        )
        self.status_label.pack(pady=(0, 20))

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path)
        if folder:
            self.download_path = folder
            self.path_label.configure(text=folder)

    def update_status(self, text: str):
        self.status_label.configure(text=text)

    def reset_ui(self):
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.progress.set(0)

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url or not re.match(r"^https?://", url, re.I):
            messagebox.showerror(
                "Invalid URL", "Please enter a valid URL (http:// or https://)."
            )
            return

        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.cancel_event.clear()
        self.progress.set(0)
        self.update_status("Connecting...")

        self.current_thread = threading.Thread(
            target=self.download_with_retry, args=(url,), daemon=True
        )
        self.current_thread.start()

    def cancel_download(self):
        self.cancel_event.set()
        self.update_status("Cancelling...")
        self.cancel_btn.configure(state="disabled")

    # ------------------------------------------------------------------
    # Retry Logic
    # ------------------------------------------------------------------
    def download_with_retry(self, url: str, max_retries: int = 3):
        for attempt in range(1, max_retries + 1):
            if self.cancel_event.is_set():
                break
            try:
                self.download_video(url)
                return
            except yt_dlp.utils.DownloadError as e:
                msg = str(e).lower()
                if "private" in msg or "unlisted" in msg:
                    self.after(0, self.on_error, "This video is private or unlisted.")
                    return
                elif "age-restricted" in msg:
                    self.after(
                        0, self.on_error, "Age-restricted video. Login not supported."
                    )
                    return
                elif "geo" in msg or "unavailable" in msg:
                    self.after(
                        0, self.on_error, "Video is geo-restricted or unavailable."
                    )
                    return
                elif "challenge" in msg:
                    self.after(
                        0, self.update_status, "YouTube challenge detected. Retrying..."
                    )
                    time.sleep(2)
                    continue
            except requests.exceptions.RequestException:
                if attempt < max_retries:
                    self.after(
                        0,
                        self.update_status,
                        f"Connection failed. Retrying in 3s... ({attempt}/{max_retries})",
                    )
                    time.sleep(3)
                    continue
                else:
                    self.after(
                        0,
                        self.on_error,
                        "Network error. Check your internet connection.",
                    )
                    return
            except Exception as e:
                if "ffmpeg" in str(e).lower():
                    self.after(
                        0,
                        self.on_error,
                        "FFmpeg missing! Place ffmpeg.exe in app folder.",
                    )
                    return
                self.after(0, self.on_error, f"Unexpected error: {str(e)[:100]}...")
                return

        if not self.cancel_event.is_set():
            self.after(0, self.on_error, "Failed after multiple retries.")


    def download_video(self, url: str):
        ffmpeg_path = FFMPEG_PATH if os.path.exists(FFMPEG_PATH) else shutil.which("ffmpeg")

        ydl_opts = {
            "outtmpl": os.path.join(self.download_path, "%(title)s.%(ext)s"),
            "progress_hooks": [self.progress_hook],
            "quiet": True,
            "noplaylist": True,
            "retries": 3,
            "fragment_retries": 3,
            "continuedl": True,
            "extractor_args": {"youtube": {"skip": ["challenge"]}},
        }
        if ffmpeg_path:
            ydl_opts["ffmpeg_location"] = ffmpeg_path
        else:
            self.after(
                0,
                self.update_status,
                "Warning: ffmpeg not found – some merges will be skipped.",
            )

        fmt = self.format_var.get()

        # Audio-only → MP3
        if fmt == "bestaudio/best":
            ydl_opts.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                }
            )
        else:
            ydl_opts["format"] = fmt
            if "ext=mp4" in fmt:
                ydl_opts["merge_output_format"] = "mp4"

        # NEW – ALWAYS merge to MP4 for the original best-quality codec
        if fmt == "bestvideo+bestaudio/best":
            ydl_opts["merge_output_format"] = "mp4"  # NEW

        if self.subs_var.get():
            ydl_opts.update(
                {
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": ["en", ".all"],
                }
            )

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            self.after(0, self.update_status, "Fetching video info...")
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "Unknown")
            ext = "mp3" if fmt == "bestaudio/best" else info.get("ext", "mp4")
            filename = f"{title}.{ext}"

            self.after(0, self.update_status, "Downloading...")
            ydl.download([url])

            if not self.cancel_event.is_set():
                self.after(0, self.on_success, filename)

    def progress_hook(self, d):
        if self.cancel_event.is_set():
            raise yt_dlp.utils.DownloadError("Cancelled by user")
        if d["status"] == "downloading":
            try:
                p = d.get("_percent_str", "0%").strip().rstrip("%")
                percent = float(p) / 100
                self.after(0, self.progress.set, percent)
                speed = (
                    d.get("_speed_str", "?")
                    .replace("MiB/s", " MB/s")
                    .replace("KiB/s", " KB/s")
                )
                eta = d.get("_eta_str", "?")
                if eta in ("?", "00:00"):
                    eta = "calculating..."
                self.after(
                    0, self.update_status, f"Downloading... {p}% | {speed} | ETA: {eta}"
                )
            except:
                pass
        elif d["status"] == "finished":
            self.after(0, self.progress.set, 1.0)
            self.after(0, self.update_status, "Finalizing...")

    def on_success(self, filename: str):
        self.progress.set(1.0)
        self.update_status(f"Success: {filename}")
        messagebox.showinfo("Download Complete", f"Saved as:\n{filename}")
        self.reset_ui()

    def on_error(self, msg: str):
        self.update_status("Failed.")
        messagebox.showerror("Download Failed", msg)
        self.reset_ui()

    # ------------------------------------------------------------------
    # About & FAQ
    # ------------------------------------------------------------------
    def show_about(self):
        win = ctk.CTkToplevel(self)
        win.title(f"About {APP_NAME}")
        win.geometry("420x400")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        self.center_window(win, 420, 400)

        frame = ctk.CTkFrame(win, corner_radius=12)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        if self.app_icon_ctk:
            img = self.app_icon_ctk._light_image.resize(
                (96, 96), Image.Resampling.LANCZOS
            )
            white_icon = Image.new("RGBA", (96, 96), (255, 255, 255, 255))
            alpha = img.split()[-1]
            white_icon = Image.composite(
                white_icon, Image.new("RGBA", (96, 96), (0, 0, 0, 0)), alpha
            )
            ctk.CTkLabel(
                frame,
                image=ctk.CTkImage(light_image=white_icon, dark_image=white_icon),
                text="",
            ).pack(pady=(20, 12))

        ctk.CTkLabel(
            frame, text=APP_NAME, font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=(0, 3))
        ctk.CTkLabel(frame, text=f"v{APP_VERSION}").pack(pady=(0, 18))
        ctk.CTkLabel(frame, text="Developed by").pack()
        ctk.CTkLabel(
            frame,
            text=APP_AUTHOR,
            font=ctk.CTkFont(size=16, weight="bold", underline=True),
            text_color="#00AAFF",
        ).pack(pady=(3, 1))
        ctk.CTkLabel(
            frame,
            text="IT Specialist - CDO and Butuan",
            font=ctk.CTkFont(size=11, slant="italic"),
        ).pack(pady=(0, 25))
        ctk.CTkLabel(frame, text=f"© {APP_YEAR} {APP_AUTHOR}").pack(pady=(20, 10))
        ctk.CTkButton(
            frame, text="Close", width=120, fg_color="#FF0000", command=win.destroy
        ).pack(pady=(5, 15))

    def show_faq(self):
        win = ctk.CTkToplevel(self)
        win.title("FAQ - Video Downloader Plus")
        win.geometry("530x500")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        self.center_window(win, 530, 500)

        main = ctk.CTkFrame(win, corner_radius=12)
        main.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(
            main,
            text="Frequently Asked Questions",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(10, 8), sticky="w", padx=15)

        canvas = ctk.CTkCanvas(main, highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(main, orientation="vertical", command=canvas.yview)
        scroll_frame = ctk.CTkFrame(canvas)
        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=1, column=0, sticky="nsew", padx=(15, 0), pady=(0, 15))
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 15))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        def on_mousewheel(event):
            delta = -1 * (
                event.delta or (event.num == 4 and -1) or (event.num == 5 and 1) or 0
            )
            canvas.yview_scroll(delta, "units")

        win.bind("<Enter>", lambda e: win.bind_all("<MouseWheel>", on_mousewheel))
        win.bind("<Leave>", lambda e: win.unbind_all("<MouseWheel>"))

        faqs = [
            (
                "Supported Platforms",
                "YouTube • TikTok • Instagram • Facebook • Twitter/X • Vimeo • SoundCloud + 1,000 more",
            ),
            ("Private Videos?", "No. Only public content is supported."),
            ("Video Formats", "MP4 (4K–480p) • WEBM • MP3 • M4A • WAV"),
            ("Need ffmpeg?", "Yes, for merging high-quality video + audio."),
            ("Playlists?", "Yes! Paste any playlist URL."),
            ("Subtitles?", "Yes, auto or manual (.srt) in English."),
            ("Legal & Safe?", "Uses yt-dlp (open-source). Personal use only."),
            ("Slow Download?", "Try lower resolution or check internet."),
        ]

        for i, (q, a) in enumerate(faqs):
            ctk.CTkLabel(
                scroll_frame,
                text=q,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#00AAFF",
                anchor="w",
            ).grid(row=i * 2, column=0, sticky="w", padx=15, pady=(8, 2))
            ctk.CTkLabel(
                scroll_frame,
                text=a,
                font=ctk.CTkFont(size=11),
                text_color="#BBB",
                anchor="w",
                wraplength=460,
            ).grid(row=i * 2 + 1, column=0, sticky="w", padx=15, pady=(0, 10))

        ctk.CTkLabel(scroll_frame, text="").grid(row=len(faqs) * 2, column=0, pady=10)

    def center_window(self, win, w, h):
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")


if __name__ == "__main__":
    app = YouTubeDownloader()
    app.mainloop()
