# pdf_merger_pro.py
# Ultimate PDF Merger – SYNCED UP/DOWN + BIGGER FONT + TALLER ROWS + HELP + ICON + ABOUT + AUTO-NAMING + SETTINGS + FEEDBACK + OFFLINE QUEUE

import os
import json
import threading
import queue
import time
import sys
from datetime import datetime
from pathlib import Path
from tkinter import (
    Tk,
    Frame,
    Label,
    Listbox,
    Scrollbar,
    filedialog,
    messagebox,
    ttk,
    END,
    BOTH,
    LEFT,
    RIGHT,
    X,
    Y,
    Button,
    Menu,
    Toplevel,
    Text,
    Checkbutton,
    Radiobutton,
    StringVar,
    IntVar,
)
from tkinterdnd2 import DND_FILES, TkinterDnD
from PyPDF2 import PdfMerger, PdfReader
from PyPDF2.errors import PdfReadError, WrongPasswordError
import requests
import pytz

# ==================== APP INFO ====================
APP_NAME = "PDF Merger Pro Plus Ultimate"
APP_VERSION = "0.1.0"
APP_AUTHOR = "Jessie Albert J. Regualos"
APP_YEAR = "2025"
# =================================================

# ==================== SMART SETTINGS PATH ====================
if getattr(sys, "frozen", False):
    APPDATA_DIR = Path(os.getenv("APPDATA")) / "PDFMergerPro"
    APPDATA_DIR.mkdir(exist_ok=True)
    SETTINGS_FILE = APPDATA_DIR / "settings.json"
    FEEDBACK_QUEUE_FILE = APPDATA_DIR / "pending_feedback.json"
else:
    SETTINGS_FILE = Path(__file__).with_name("settings.json")
    FEEDBACK_QUEUE_FILE = Path(__file__).with_name("pending_feedback.json")
# ============================================================

# ==================== SUPABASE CONFIG (GMT+8 Manila) ====================
SUPABASE_URL = "https://cnsqlixkahntrzfxkndz.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNuc3FsaXhrYWhudHJ6ZnhrbmR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMxNTQ0MTUsImV4cCI6MjA3ODczMDQxNX0.hhuwWCuhFyEfy5iE4067qHlJf2BKpyTY6Xpqga83srk"
SUPABASE_TABLE = "feedback"
MANILA_TZ = pytz.timezone("Asia/Manila")
# =====================================================================

# ==================== FEEDBACK QUEUE ====================
feedback_queue = queue.Queue()


def load_pending_feedback():
    if FEEDBACK_QUEUE_FILE.exists():
        try:
            with open(FEEDBACK_QUEUE_FILE, "r", encoding="utf-8") as f:
                items = json.load(f)
                for it in items:
                    feedback_queue.put(it)
        except Exception:
            pass


def save_pending_feedback():
    items = list(feedback_queue.queue)
    try:
        with open(FEEDBACK_QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=4)
    except Exception:
        pass


def submit_feedback(rating: int, name: str | None, comment: str):
    payload = {
        "rating": rating,
        "name": name.strip() if name and name.strip() else None,
        "comment": comment.strip(),
        "created_at": datetime.now(MANILA_TZ).isoformat(),
    }
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}",
            json=payload,
            headers=headers,
            timeout=8,
        )
        if resp.status_code in (200, 201):
            return True, "Thank you! Your feedback was saved."
        else:
            raise Exception(f"Server {resp.status_code}")
    except Exception:
        feedback_queue.put(payload)
        save_pending_feedback()
        return (
            True,
            "No internet – your feedback will be sent next time you open the app.",
        )


def feedback_worker():
    while True:
        time.sleep(30)
        if feedback_queue.empty():
            continue
        payload = feedback_queue.queue[0]
        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}",
                json=payload,
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                timeout=8,
            )
            if resp.status_code in (200, 201):
                feedback_queue.get()
                save_pending_feedback()
        except Exception:
            pass


# =====================================================================


class PDFMergerPro:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1000x700")
        self.root.minsize(800, 580)
        self.root.configure(bg="#0f0f1a")

        # Set App Icon
        icon_path = Path("icons/pdf_merger.ico")
        if getattr(sys, "frozen", False):
            bundle_dir = Path(sys._MEIPASS)
            icon_path = bundle_dir / "icons" / "pdf_merger.ico"
        if icon_path.exists():
            self.root.iconbitmap(icon_path)

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.on_drop)

        self.files = []
        self.dragging = False
        self.drag_start_idx = None

        # ---- Settings -------------------------------------------------
        self.settings = self.load_settings()
        self.auto_naming = self.settings.get("auto_naming", True)
        self.default_folder = self.settings.get("default_folder", "desktop")
        self.custom_path = self.settings.get("custom_path", "")

        # ---- Load offline feedback + start retry worker ----
        load_pending_feedback()
        threading.Thread(target=feedback_worker, daemon=True).start()

        self.setup_ui()
        self.create_styles()

        # Hide listbox + scrollbar at start
        self.listbox.grid_remove()
        self.scrollbar.grid_remove()

    # ------------------------------------------------------------------
    def load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_settings(self):
        data = {
            "auto_naming": self.auto_naming,
            "default_folder": self.default_folder,
        }
        if self.default_folder == "custom":
            data["custom_path"] = self.custom_path
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def create_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TProgressbar", thickness=24, background="#00ff88", troughcolor="#1e1e2e"
        )

    # ------------------------------------------------------------------
    def setup_ui(self):
        main_frame = Frame(self.root, bg="#0f0f1a")
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # Title
        Label(
            main_frame,
            text=APP_NAME,
            font=("Segoe UI", 26, "bold"),
            fg="#00ddff",
            bg="#0f0f1a",
            anchor="w",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        Label(
            main_frame,
            text="Drag & drop PDFs • Sort with Up/Down • Merge with progress",
            font=("Segoe UI", 11),
            fg="#88aaff",
            bg="#0f0f1a",
            anchor="w",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 15))

        # Top Right: Rate App + Settings + Help + About
        top_right = Frame(main_frame, bg="#0f0f1a")
        top_right.grid(row=0, column=2, sticky="ne", pady=(0, 8))

        self.create_small_button(
            top_right, "Rate App", "#ffaa00", self.show_rating
        ).pack(side=RIGHT, padx=3)
        self.create_small_button(
            top_right, "Settings", "#ffaa00", self.show_settings
        ).pack(side=RIGHT, padx=3)
        self.create_small_button(top_right, "Help", "#00aaff", self.show_help).pack(
            side=RIGHT, padx=3
        )
        self.create_small_button(top_right, "About", "#00ff88", self.show_about).pack(
            side=RIGHT
        )

        # File List Container
        list_container = Frame(main_frame, bg="#16213e", relief="flat", bd=2)
        list_container.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(0, 15))
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(1, weight=1)

        # Up/Down Buttons
        btn_frame = Frame(list_container, bg="#16213e")
        btn_frame.grid(row=0, column=0, sticky="ns", padx=(10, 5), pady=10)
        self.up_btn = self.create_big_button(
            btn_frame, "UP", "#00aaff", self.move_up, height=3, width=10
        )
        self.up_btn.pack(fill=X, pady=5)
        self.down_btn = self.create_big_button(
            btn_frame, "DOWN", "#00aaff", self.move_down, height=3, width=10
        )
        self.down_btn.pack(fill=X, pady=5)

        # Listbox Frame
        listbox_frame = Frame(list_container, bg="#16213e")
        listbox_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        listbox_frame.grid_columnconfigure(0, weight=1)
        listbox_frame.grid_rowconfigure(0, weight=1)

        # Drop Hint
        self.drop_hint = Label(
            listbox_frame,
            text="Drop PDF files here",
            font=("Consolas", 12),
            fg="#666",
            bg="#16213e",
            height=4,
            anchor="center",
        )
        self.drop_hint.grid(row=0, column=0, sticky="nsew")

        # Listbox – BIGGER FONT + TALLER ROWS
        self.listbox = Listbox(
            listbox_frame,
            bg="#1e1e2e",
            fg="#e0e0e0",
            font=("Consolas", 18, "bold"),
            selectbackground="#00aaff",
            selectforeground="white",
            bd=0,
            highlightthickness=0,
            activestyle="none",
            height=10,
            relief="flat",
        )
        self.listbox.bind("<ButtonPress-1>", self.on_drag_start)
        self.listbox.bind("<B1-Motion>", self.on_drag_motion)
        self.listbox.bind("<ButtonRelease-1>", self.on_drag_release)

        # Scrollbar
        self.scrollbar = Scrollbar(listbox_frame, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=self.scrollbar.set)

        # Grid both (hidden at start)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Context menu
        self.context_menu = Menu(
            self.root, tearoff=0, bg="#1e1e2e", fg="white", font=("Segoe UI", 9)
        )
        self.context_menu.add_command(label="Remove", command=self.remove_selected)
        self.listbox.bind("<Button-3>", self.show_context_menu)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self.update_buttons())

        # Control Buttons
        ctrl_frame = Frame(main_frame, bg="#0f0f1a")
        ctrl_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        ctrl_frame.grid_columnconfigure(0, weight=1)
        ctrl_frame.grid_columnconfigure(1, weight=1)
        self.create_big_button(
            ctrl_frame, "Add PDFs", "#00aaff", self.add_files, width=20
        ).grid(row=0, column=0, padx=8, sticky="e")
        self.create_big_button(
            ctrl_frame, "Clear All", "#ff5555", self.clear_files, width=20
        ).grid(row=0, column=1, padx=8, sticky="w")

        # Progress + Merge
        bottom_frame = Frame(main_frame, bg="#0f0f1a")
        bottom_frame.grid(row=4, column=0, columnspan=3, sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)

        prog_frame = Frame(bottom_frame, bg="#16213e", relief="flat", bd=2)
        prog_frame.pack(fill=X, pady=(0, 10), padx=5)
        self.progress = ttk.Progressbar(prog_frame, mode="determinate", maximum=100)
        self.progress.pack(fill=X, padx=15, pady=(15, 8))
        self.progress_label = Label(
            prog_frame, text="Ready", fg="#aaa", bg="#16213e", font=("Consolas", 10)
        )
        self.progress_label.pack(pady=(0, 15))

        self.merge_btn = self.create_big_button(
            bottom_frame,
            "MERGE PDFs",
            "#00ff88",
            self.start_merge,
            font=("Segoe UI", 16, "bold"),
            height=2,
            state="disabled",
        )
        self.merge_btn.pack(fill=X, pady=(5, 0), padx=5)

        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        self.update_buttons()

    # ------------------------------------------------------------------
    def create_big_button(self, parent, text, bg, command, **kw):
        font = kw.pop("font", ("Segoe UI", 11, "bold"))
        width = kw.pop("width", 12)
        height = kw.pop("height", 2)
        btn = Button(
            parent,
            text=text,
            bg=bg,
            fg="white",
            font=font,
            relief="flat",
            command=command,
            cursor="hand2",
            bd=0,
            highlightthickness=0,
            width=width,
            height=height,
            **kw,
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=self.lighten(bg)))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def create_small_button(self, parent, text, bg, command):
        btn = Button(
            parent,
            text=text,
            bg=bg,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            command=command,
            cursor="hand2",
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=3,
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=self.lighten(bg)))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def lighten(self, hex_color):
        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
        lighter = tuple(min(255, int(c * 1.35)) for c in rgb)
        return f"#{lighter[0]:02x}{lighter[1]:02x}{lighter[2]:02x}"

    # ------------------------------------------------------------------
    def center_over_parent(self, child, width, height):
        child.update_idletasks()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()
        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2
        child.geometry(f"{width}x{height}+{x}+{y}")

    # ------------------------------------------------------------------
    def show_rating(self):
        rating_win = Toplevel(self.root)
        rating_win.title("Rate PDF Merger Pro")
        rating_win.configure(bg="#0f0f1a")
        rating_win.transient(self.root)
        rating_win.grab_set()
        rating_win.resizable(False, False)
        rating_win.geometry("540x700")
        self.center_over_parent(rating_win, 540, 590)

        icon_path = Path("icons/pdf_merger.ico")
        if getattr(sys, "frozen", False):
            icon_path = Path(sys._MEIPASS) / "icons" / "pdf_merger.ico"
        if icon_path.exists():
            rating_win.iconbitmap(icon_path)

        frame = Frame(rating_win, bg="#0f0f1a")
        frame.pack(fill=BOTH, expand=True, padx=30, pady=30)

        Label(
            frame,
            text="Rate Your Experience",
            font=("Segoe UI", 19, "bold"),
            fg="#00ddff",
            bg="#0f0f1a",
        ).pack(anchor="w", pady=(0, 20))

        star_frame = Frame(frame, bg="#0f0f1a")
        star_frame.pack(pady=(0, 22))
        selected_rating = IntVar(value=0)

        def set_rating(val):
            selected_rating.set(val)
            for i in range(5):
                stars[i].config(
                    text="★" if i < val else "☆",
                    fg="#ffd700" if i < val else "#666",
                )

        def hover_stars(val):
            for i in range(5):
                stars[i].config(fg="#ffd700" if i < val else "#666")

        stars = []
        for i in range(1, 6):
            lbl = Label(
                star_frame,
                text="☆",
                font=("Segoe UI", 40),
                fg="#666",
                bg="#0f0f1a",
                cursor="hand2",
            )
            lbl.pack(side=LEFT, padx=8)
            lbl.bind("<Button-1>", lambda e, v=i: set_rating(v))
            lbl.bind("<Enter>", lambda e, v=i: hover_stars(v))
            stars.append(lbl)

        star_frame.bind("<Leave>", lambda e: set_rating(selected_rating.get()))

        Label(
            frame,
            text="Your Name (optional)",
            font=("Segoe UI", 11),
            fg="#cccccc",
            bg="#0f0f1a",
        ).pack(anchor="w", pady=(10, 4))
        name_var = StringVar()
        name_entry = ttk.Entry(
            frame, textvariable=name_var, width=48, font=("Consolas", 11)
        )
        name_entry.pack(fill=X, pady=(0, 18))

        Label(
            frame,
            text="Comment (required)",
            font=("Segoe UI", 11),
            fg="#cccccc",
            bg="#0f0f1a",
        ).pack(anchor="w", pady=(0, 4))
        comment_text = Text(
            frame,
            height=6,
            bg="#1e1e2e",
            fg="#e0e0e0",
            font=("Consolas", 11),
            wrap="word",
            relief="flat",
            bd=2,
            insertbackground="#00ddff",
        )
        comment_text.pack(fill=X, pady=(0, 25))

        # ---------- STATUS ----------
        status_label = Label(
            frame,
            text="",
            fg="#ffaa00",
            bg="#0f0f1a",
            font=("Consolas", 10),
            wraplength=460,
        )
        status_label.pack(pady=(0, 20))

        # ---------- CENTERED BUTTONS ----------
        btn_frame = Frame(frame, bg="#0f0f1a")
        btn_frame.pack(pady=(10, 0))

        # Helper for hover
        def btn_hover_enter(e, btn, base):
            btn.config(bg=self.lighten(base))

        def btn_hover_leave(e, btn, base):
            btn.config(bg=base)

        # Submit Button
        submit_btn = Button(
            btn_frame,
            text="Submit Feedback",
            bg="#00ff88",
            fg="black",
            font=("Segoe UI", 13, "bold"),
            relief="flat",
            cursor="hand2",
            padx=35,
            pady=14,
            width=16,
        )
        submit_btn.pack(side=LEFT, padx=8)
        submit_btn.bind("<Enter>", lambda e: btn_hover_enter(e, submit_btn, "#00ff88"))
        submit_btn.bind("<Leave>", lambda e: btn_hover_leave(e, submit_btn, "#00ff88"))

        # Cancel Button
        cancel_btn = Button(
            btn_frame,
            text="Cancel",
            bg="#ff5555",
            fg="white",
            font=("Segoe UI", 13, "bold"),
            relief="flat",
            cursor="hand2",
            padx=35,
            pady=14,
            width=12,
        )
        cancel_btn.pack(side=LEFT, padx=8)
        cancel_btn.bind("<Enter>", lambda e: btn_hover_enter(e, cancel_btn, "#ff5555"))
        cancel_btn.bind("<Leave>", lambda e: btn_hover_leave(e, cancel_btn, "#ff5555"))

        # Center the button frame
        btn_frame.pack(anchor="center")

        def do_submit():
            rating = selected_rating.get()
            if rating == 0:
                status_label.config(text="Please select a star rating.", fg="#ffaa00")
                return
            comment = comment_text.get("1.0", END).strip()
            if not comment:
                status_label.config(text="Please write a comment.", fg="#ffaa00")
                return
            if len(comment) < 5:
                status_label.config(
                    text="Comment too short (min 5 chars).", fg="#ffaa00"
                )
                return

            status_label.config(text="Submitting…", fg="#aaa")
            submit_btn.config(state="disabled")
            cancel_btn.config(state="disabled")
            rating_win.update_idletasks()

            def thread_job():
                success, msg = submit_feedback(rating, name_var.get(), comment)
                self.root.after(0, lambda: finalize(success, msg))

            threading.Thread(target=thread_job, daemon=True).start()

        def finalize(success, msg):
            status_label.config(
                text=msg,
                fg="#00ff88" if "saved" in msg or "next time" in msg else "#ff5555",
            )
            if success:
                rating_win.after(1400, rating_win.destroy)
            else:
                submit_btn.config(state="normal")
                cancel_btn.config(state="normal")

        submit_btn.config(command=do_submit)
        cancel_btn.config(command=rating_win.destroy)

    # ------------------------------------------------------------------
    def show_help(self):
        help_win = Toplevel(self.root)
        help_win.title("Help - How to Use PDF Merger Pro")
        help_win.configure(bg="#0f0f1a")
        help_win.transient(self.root)
        help_win.grab_set()
        help_win.resizable(False, False)
        help_win.geometry("700x580")
        self.center_over_parent(help_win, 700, 580)

        icon_path = Path("icons/pdf_merger.ico")
        if getattr(sys, "frozen", False):
            icon_path = Path(sys._MEIPASS) / "icons" / "pdf_merger.ico"
        if icon_path.exists():
            help_win.iconbitmap(icon_path)

        frame = Frame(help_win, bg="#0f0f1a")
        frame.pack(fill=BOTH, expand=True, padx=15, pady=15)

        Label(
            frame,
            text="How to Use PDF Merger Pro",
            font=("Segoe UI", 16, "bold"),
            fg="#00ddff",
            bg="#0f0f1a",
        ).pack(anchor="w", pady=(0, 10))

        text = Text(
            frame,
            bg="#1e1e2e",
            fg="#e0e0e0",
            font=("Consolas", 11),
            wrap="word",
            relief="flat",
            padx=10,
            pady=10,
        )
        text.pack(fill=BOTH, expand=True)

        help_text = """
FEATURES & INSTRUCTIONS

1. ADD PDF FILES
   • Click "Add PDFs" button
   • Or DRAG & DROP PDF files directly into the app
   • Duplicate files are automatically ignored

2. REORDER FILES
   • Select a file in the list
   • Use UP / DOWN buttons
   • Or DRAG with mouse to reorder (click & hold)

3. REMOVE FILES
   • Right-click any file → "Remove"

4. MERGE PDFs
   • Need at least 2 valid PDFs
   • Click "MERGE PDFs"
   • Choose save location (auto-suggested if enabled)
   • Progress bar shows real-time merge status

5. SETTINGS
   • Gear icon → Settings
   • Enable/disable auto-naming
   • Choose default output folder

6. RATE APP
   • Click "Rate App" to submit feedback
   • Works offline – saved & sent later
   • Your time is saved in Manila (GMT+8)

7. SUPPORTED ISSUES
   • Skips corrupted, password-protected, or empty PDFs
   • Shows detailed error list if merge fails

Enjoy fast, clean, and professional PDF merging!

— Developed with love by Jessie Albert J. Regualos
        """
        text.insert(END, help_text.strip())
        text.config(state="disabled")

        Button(
            frame,
            text="Close",
            bg="#ff5555",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            command=help_win.destroy,
            relief="flat",
            padx=20,
            cursor="hand2",
        ).pack(pady=(10, 0))

    # ------------------------------------------------------------------
    def show_about(self):
        about_win = Toplevel(self.root)
        about_win.title(f"About {APP_NAME}")
        about_win.configure(bg="#0f0f1a")
        about_win.transient(self.root)
        about_win.grab_set()
        about_win.resizable(False, False)
        about_win.geometry("400x300")
        self.center_over_parent(about_win, 400, 300)

        icon_path = Path("icons/pdf_merger.ico")
        if getattr(sys, "frozen", False):
            icon_path = Path(sys._MEIPASS) / "icons" / "pdf_merger.ico"
        if icon_path.exists():
            about_win.iconbitmap(icon_path)

        frame = Frame(about_win, bg="#0f0f1a")
        frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        Label(
            frame,
            text=APP_NAME,
            font=("Segoe UI", 18, "bold"),
            fg="#00ddff",
            bg="#0f0f1a",
        ).pack(pady=(0, 5))
        Label(
            frame,
            text=f"Version {APP_VERSION}",
            font=("Segoe UI", 10),
            fg="#88aaff",
            bg="#0f0f1a",
        ).pack(pady=(0, 10))
        Label(
            frame,
            text=f"© {APP_YEAR} {APP_AUTHOR}",
            font=("Segoe UI", 10),
            fg="#cccccc",
            bg="#0f0f1a",
        ).pack(pady=(0, 5))
        Label(
            frame,
            text="IT Specialist - CDO and Butuan",
            font=("Segoe UI", 9, "italic"),
            fg="#aaaaaa",
            bg="#0f0f1a",
        ).pack(pady=(0, 15))
        Label(
            frame,
            text="Merge PDFs with style, speed, and control.",
            font=("Consolas", 9),
            fg="#88ff88",
            bg="#0f0f1a",
            wraplength=340,
        ).pack(pady=(0, 20))

        Button(
            frame,
            text="Close",
            bg="#00aaff",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            command=about_win.destroy,
            relief="flat",
            padx=20,
            cursor="hand2",
        ).pack()

    # ------------------------------------------------------------------
    def show_settings(self):
        settings_win = Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.configure(bg="#0f0f1a")
        settings_win.transient(self.root)
        settings_win.grab_set()
        settings_win.resizable(False, False)
        settings_win.geometry("600x400")
        self.center_over_parent(settings_win, 600, 400)

        icon_path = Path("icons/pdf_merger.ico")
        if getattr(sys, "frozen", False):
            icon_path = Path(sys._MEIPASS) / "icons" / "pdf_merger.ico"
        if icon_path.exists():
            settings_win.iconbitmap(icon_path)

        frame = Frame(settings_win, bg="#0f0f1a")
        frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        Label(
            frame,
            text="PDF Merger Settings",
            font=("Segoe UI", 16, "bold"),
            fg="#00ddff",
            bg="#0f0f1a",
        ).pack(anchor="w", pady=(0, 15))

        auto_var = IntVar(value=1 if self.auto_naming else 0)
        Checkbutton(
            frame,
            text="Enable auto-naming (Merged_YYYY-MM-DD_HH-MM-SS.pdf)",
            variable=auto_var,
            bg="#0f0f1a",
            fg="#e0e0e0",
            selectcolor="#1e1e2e",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 15))

        folder_var = StringVar(value=self.default_folder)

        Label(
            frame,
            text="Default output folder:",
            font=("Segoe UI", 10),
            fg="#cccccc",
            bg="#0f0f1a",
        ).pack(anchor="w")
        Radiobutton(
            frame,
            text="Desktop",
            variable=folder_var,
            value="desktop",
            bg="#0f0f1a",
            fg="#e0e0e0",
            selectcolor="#1e1e2e",
        ).pack(anchor="w")
        Radiobutton(
            frame,
            text="Documents",
            variable=folder_var,
            value="documents",
            bg="#0f0f1a",
            fg="#e0e0e0",
            selectcolor="#1e1e2e",
        ).pack(anchor="w")
        Radiobutton(
            frame,
            text="Same as first PDF",
            variable=folder_var,
            value="first",
            bg="#0f0f1a",
            fg="#e0e0e0",
            selectcolor="#1e1e2e",
        ).pack(anchor="w")
        custom_radio = Radiobutton(
            frame,
            text="Custom folder",
            variable=folder_var,
            value="custom",
            bg="#0f0f1a",
            fg="#e0e0e0",
            selectcolor="#1e1e2e",
        )
        custom_radio.pack(anchor="w", pady=(0, 10))

        custom_frame = Frame(frame, bg="#0f0f1a")
        custom_frame.pack(fill=X, pady=(0, 15))

        self.custom_path_var = StringVar(value=self.custom_path)
        entry = ttk.Entry(custom_frame, textvariable=self.custom_path_var, width=40)
        entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

        ttk.Button(
            custom_frame,
            text="Browse",
            command=lambda: self.browse_custom_folder(folder_var),
        ).pack(side=RIGHT)

        btn_frame = Frame(frame, bg="#0f0f1a")
        btn_frame.pack(fill=X, pady=(10, 0))

        def save():
            self.auto_naming = bool(auto_var.get())
            self.default_folder = folder_var.get()
            if self.default_folder == "custom":
                self.custom_path = self.custom_path_var.get()
            self.save_settings()
            settings_win.destroy()

        Button(
            btn_frame,
            text="Save",
            bg="#00ff88",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            command=save,
            relief="flat",
            padx=20,
        ).pack(side=RIGHT, padx=5)
        Button(
            btn_frame,
            text="Cancel",
            bg="#ff5555",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            command=settings_win.destroy,
            relief="flat",
            padx=20,
        ).pack(side=RIGHT)

    def browse_custom_folder(self, folder_var):
        folder = filedialog.askdirectory()
        if folder:
            self.custom_path_var.set(folder)
            folder_var.set("custom")

    # ------------------------------------------------------------------
    def get_default_output_path(self):
        if not self.files:
            return Path.home() / "Desktop"
        if self.default_folder == "desktop":
            return Path.home() / "Desktop"
        elif self.default_folder == "documents":
            return Path.home() / "Documents"
        elif self.default_folder == "first":
            return Path(self.files[0]).parent
        elif self.default_folder == "custom":
            if self.custom_path and Path(self.custom_path).exists():
                return Path(self.custom_path)
            return Path.home() / "Desktop"
        return Path(self.files[0]).parent

    def generate_auto_name(self):
        timestamp = datetime.now(MANILA_TZ).strftime("%Y-%m-%d_%H-%M-%S")
        return f"Merged_{timestamp}.pdf"

    # ------------------------------------------------------------------
    def start_merge(self):
        if len(self.files) < 2:
            messagebox.showwarning("Warning", "Please add at least 2 PDF files.")
            return

        initial_dir = self.get_default_output_path()
        initial_file = self.generate_auto_name() if self.auto_naming else ""

        output = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            title="Save Merged PDF As",
            initialdir=str(initial_dir),
            initialfile=initial_file,
        )
        if not output:
            return

        self.merge_btn.config(state="disabled")
        self.progress["value"] = 0
        self.progress_label.config(text="Scanning files...")

        thread = threading.Thread(
            target=self.validate_and_merge,
            args=(self.files.copy(), output),
            daemon=True,
        )
        thread.start()

    # ------------------------------------------------------------------
    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        self.add_to_list(files)

    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        pdfs = [f for f in files if f.lower().endswith(".pdf")]
        self.add_to_list(pdfs)

    def add_to_list(self, file_list):
        added = False
        for f in file_list:
            path = Path(f)
            if path.exists() and str(path) not in self.files:
                self.files.append(str(path))
                added = True
        if added:
            self.refresh_listbox()
            self.drop_hint.grid_remove()
            self.listbox.grid()
            self.scrollbar.grid()
        self.update_buttons()

    def refresh_listbox(self):
        self.listbox.delete(0, END)
        for idx, path in enumerate(self.files, start=1):
            name = os.path.basename(path)
            self.listbox.insert(END, f"{idx:2d}. {name}")

    def clear_files(self):
        self.files.clear()
        self.listbox.delete(0, END)
        self.listbox.grid_remove()
        self.scrollbar.grid_remove()
        self.drop_hint.grid(row=0, column=0, sticky="nsew")
        self.update_buttons()

    def remove_selected(self):
        selection = self.listbox.curselection()
        for i in reversed(selection):
            self.files.pop(i)
            self.listbox.delete(i)
        if not self.files:
            self.listbox.grid_remove()
            self.scrollbar.grid_remove()
            self.drop_hint.grid(row=0, column=0, sticky="nsew")
        else:
            self.refresh_listbox()
        self.update_buttons()

    def show_context_menu(self, event):
        try:
            index = self.listbox.nearest(event.y)
            if 0 <= index < len(self.files):
                self.listbox.selection_clear(0, END)
                self.listbox.selection_set(index)
                self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def update_buttons(self):
        has_files = len(self.files) > 0
        sel = self.listbox.curselection()
        has_sel = len(sel) == 1
        idx = sel[0] if has_sel else -1
        self.merge_btn.config(state="normal" if len(self.files) > 1 else "disabled")
        self.up_btn.config(state="normal" if has_sel and idx > 0 else "disabled")
        self.down_btn.config(
            state="normal" if has_sel and idx < len(self.files) - 1 else "disabled"
        )
        if not has_files:
            self.up_btn.config(state="disabled")
            self.down_btn.config(state="disabled")

    def on_drag_start(self, event):
        idx = self.listbox.nearest(event.y)
        if 0 <= idx < len(self.files):
            self.drag_start_idx = idx
            self.dragging = True
            self.listbox.config(cursor="hand2")
            self.listbox.selection_clear(0, END)
            self.listbox.selection_set(idx)
            return "break"

    def on_drag_motion(self, event):
        if not self.dragging:
            return
        idx = self.listbox.nearest(event.y)
        if idx != self.drag_start_idx and 0 <= idx < len(self.files):
            item = self.files.pop(self.drag_start_idx)
            self.files.insert(idx, item)
            self.refresh_listbox()
            self.drag_start_idx = idx
            self.listbox.selection_set(idx)
            self.update_buttons()
        return "break"

    def on_drag_release(self, event):
        if self.dragging:
            self.dragging = False
            self.drag_start_idx = None
            self.listbox.config(cursor="")
            self.update_buttons()
        return "break"

    def move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.files[i], self.files[i - 1] = self.files[i - 1], self.files[i]
        self.refresh_listbox()
        self.listbox.selection_set(i - 1)
        self.update_buttons()

    def move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == len(self.files) - 1:
            return
        i = sel[0]
        self.files[i], self.files[i + 1] = self.files[i + 1], self.files[i]
        self.refresh_listbox()
        self.listbox.selection_set(i + 1)
        self.update_buttons()

    def validate_and_merge(self, pdf_list, output_path):
        errors = []
        valid_files = []
        total_pages = 0

        for pdf in pdf_list:
            filename = os.path.basename(pdf)
            if not os.path.exists(pdf):
                errors.append(f"Missing: {filename}")
                continue

            try:
                reader = PdfReader(pdf)
                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                    except WrongPasswordError:
                        errors.append(f"Password protected: {filename}")
                        continue
                    except:
                        errors.append(f"Password protected: {filename}")
                        continue

                page_count = len(reader.pages)
                if page_count == 0:
                    errors.append(f"Empty PDF: {filename}")
                    continue

                valid_files.append(pdf)
                total_pages += page_count

            except PdfReadError:
                errors.append(f"Corrupted: {filename}")
            except Exception:
                errors.append(f"Cannot read: {filename}")

        if errors:
            self.root.after(
                0,
                lambda: [
                    self.progress.config(value=0),
                    self.progress_label.config(text="Failed"),
                    self.merge_btn.config(
                        state="normal" if len(self.files) > 1 else "disabled"
                    ),
                    messagebox.showerror(
                        "Cannot Merge",
                        "The following files cannot be merged:\n\n"
                        + "\n".join(f"• {e}" for e in errors),
                    ),
                ],
            )
            return

        if len(valid_files) < 2:
            self.root.after(
                0,
                lambda: [
                    self.progress.config(value=0),
                    self.progress_label.config(text="Failed"),
                    self.merge_btn.config(state="normal"),
                    messagebox.showerror("Cannot Merge", "Need at least 2 valid PDFs."),
                ],
            )
            return

        self.root.after(0, lambda: self.progress_label.config(text="Merging... 0%"))
        self.actual_merge(valid_files, output_path, total_pages)

    def actual_merge(self, valid_files, output_path, total_pages):
        merger = PdfMerger()
        processed = 0

        for pdf in valid_files:
            try:
                reader = PdfReader(pdf)
                pages = len(reader.pages)
                merger.append(pdf)
                processed += pages
                percent = int((processed / total_pages) * 100)
                self.root.after(
                    0,
                    lambda p=percent: [
                        self.progress.config(value=p),
                        self.progress_label.config(text=f"Merging... {p}%"),
                    ],
                )
            except Exception:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Merge Error", f"Failed during merge: {os.path.basename(pdf)}"
                    ),
                )
                self.finish_merge()
                return

        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            merger.write(output_path)
            merger.close()
            self.root.after(
                0,
                lambda: [
                    self.progress.config(value=100),
                    self.progress_label.config(text="Saving..."),
                    messagebox.showinfo(
                        "Success!",
                        f"Merged {len(valid_files)} file(s)\n"
                        f"{total_pages} page(s) total\n"
                        f"Saved to:\n{output_path}",
                    ),
                ],
            )
        except Exception as e:
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Save Failed", f"Could not save file:\n{e}"
                ),
            )

        self.finish_merge()

    def finish_merge(self):
        self.root.after(
            0,
            lambda: [
                self.progress_label.config(text="Done"),
                self.merge_btn.config(
                    state="normal" if len(self.files) > 1 else "disabled"
                ),
            ],
        )


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = PDFMergerPro(root)
    root.mainloop()
