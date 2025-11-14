# gui/main_window.py
import threading
import os
from tkinter import (
    Tk,
    Label,
    Frame,
    Menu,
    StringVar,
    IntVar,
    DoubleVar,
    filedialog,
    messagebox,
    ttk,
)
from .rounded_button import RoundedButton
from .settings_window import open_settings
from .about_window import open_about
from .popup import show_completion_popup
from core.pdf_compressor import compress_pdf_to_target
from core.office_compressor import compress_office_to_target
from core.image_compressor import compress_image
from utils.helpers import get_compressed_name


class CompressMasterApp:
    def __init__(self):
        self.root = Tk()
        self.root.title("CompressMaster")
        self.root.geometry("560x500")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e1e")  # Dark theme

        self.selected_file = StringVar()
        self.compression_mode = IntVar(value=1)
        self.compression_rate = IntVar(value=75)
        self.target_size = DoubleVar(value=2.0)

        self.setup_menu()
        self.setup_ui()

    def setup_menu(self):
        menu = Menu(self.root)
        menu.add_command(
            label="Settings",
            command=lambda: open_settings(
                self.root,
                self.compression_mode,
                self.compression_rate,
                self.target_size,
            ),
        )
        menu.add_command(label="About", command=lambda: open_about(self.root))
        menu.add_separator()
        menu.add_command(label="Exit", command=self.root.quit)
        self.root.config(menu=menu)

    def setup_ui(self):
        Label(
            self.root,
            text="CompressMaster",
            font=("Segoe UI", 22, "bold"),
            fg="white",
            bg="#333",
        ).pack(pady=25)

        Label(self.root, text="Selected File:", fg="#aaa", bg="#1e1e1e").pack(
            pady=(20, 5)
        )
        self.file_label = Label(
            self.root,
            text="(No file selected)",
            bg="#333",
            fg="#888",
            relief="solid",
            bd=1,
            padx=15,
            pady=12,
            width=60,
        )
        self.file_label.pack(pady=5)

        btns = Frame(self.root, bg="#1e1e1e")
        btns.pack(pady=25)
        RoundedButton(btns, "Browse", self.select_file, "#2196F3", "#1976D2").pack(
            side="left", padx=25
        )
        RoundedButton(
            btns, "Compress", self.start_compression, "#4CAF50", "#388E3C", width=200
        ).pack(side="right", padx=25)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TProgressbar", background="#4CAF50", troughcolor="#333", thickness=30
        )
        self.progress = ttk.Progressbar(
            self.root, length=460, style="TProgressbar", mode="determinate"
        )
        self.progress.pack(pady=25)

        self.status = Label(
            self.root,
            text="Ready",
            fg="#aaa",
            bg="#1e1e1e",
            font=("Segoe UI", 11, "bold"),
        )
        self.status.pack()

        Label(
            self.root,
            text="PDF • DOCX • XLSX • JPG • PNG • WebP",
            fg="#666",
            bg="#1e1e1e",
            font=("Segoe UI", 9, "italic"),
        ).pack(side="bottom", pady=20)

    # FIXED: Renamed from selectrombin_file
    def select_file(self):
        path = filedialog.askopenfilename(
            filetypes=[
                (
                    "All Supported",
                    "*.pdf *.docx *.xlsx *.jpg *.jpeg *.png *.webp *.bmp",
                ),
                ("PDF", "*.pdf"),
                ("Office", "*.docx *.xlsx"),
                ("Images", "*.jpg *.jpeg *.png *.webp *.bmp"),
            ]
        )
        if path:
            self.selected_file.set(path)
            self.file_label.config(text=os.path.basename(path), fg="white")

    def start_compression(self):
        path = self.selected_file.get()
        if not path:
            return messagebox.showwarning("No File", "Select a file first!")

        ext = os.path.splitext(path)[1].lower()
        output_path = filedialog.asksaveasfilename(
            initialfile=os.path.basename(get_compressed_name(path)),
            defaultextension=ext,
            filetypes=[(ext[1:].upper(), f"*{ext}")],
        )
        if not output_path:
            return

        threading.Thread(
            target=self.compress_file, args=(path, output_path), daemon=True
        ).start()

    def compress_file(self, input_path, output_path):
        def update(pct, txt):
            self.progress["value"] = pct
            self.status.config(text=txt)
            self.root.update_idletasks()

        self.progress["value"] = 0
        update(0, "Analyzing...")

        try:
            size_mb = os.path.getsize(input_path) / (1024 * 1024)
            target_bytes = (
                size_mb * 1024 * 1024 * (100 - self.compression_rate.get()) / 100
                if self.compression_mode.get() == 1 or size_mb < 1
                else self.target_size.get() * 1024 * 1024
            )

            update(10, "Processing...")

            ext = os.path.splitext(input_path)[1].lower()
            success = False
            final_size = 0

            if ext == ".pdf":
                success, final_size = compress_pdf_to_target(
                    input_path, output_path, target_bytes, update
                )
            elif ext in {".docx", ".xlsx"}:
                success, final_size = compress_office_to_target(
                    input_path, output_path, target_bytes, update
                )
            elif ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                success, final_size = compress_image(
                    input_path, output_path, quality=self.compression_rate.get()
                )
                update(100, "Done!")
            else:
                messagebox.showerror("Error", "Unsupported file!")
                return

            if success and final_size < os.path.getsize(input_path) * 0.9:
                self.root.after(
                    0,
                    show_completion_popup,
                    self.root,
                    input_path,
                    output_path,
                    size_mb,
                    final_size / (1024 * 1024),
                    (os.path.getsize(input_path) - final_size) / 1024,
                    self.reset_ui,
                )
            else:
                self.root.after(
                    0, lambda: messagebox.showinfo("Done", "No further compression.")
                )

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed:\n{e}"))
        finally:
            update(0, "Ready")

    def reset_ui(self):
        self.selected_file.set("")
        self.file_label.config(text="(No file selected)", fg="#888")
        self.progress["value"] = 0
        self.status.config(text="Ready")

    def run(self):
        self.root.mainloop()
