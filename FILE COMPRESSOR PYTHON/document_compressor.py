import os
import shutil
import threading
import tempfile
import zipfile
import logging
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import NameObject, NumberObject
from PIL import Image
from io import BytesIO

# ========================================
#               LOGGING SETUP
# ========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("compression.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ========================================
#          ROUNDED BUTTON CLASS
# ========================================
class RoundedButton(Canvas):
    def __init__(
        self,
        parent,
        text,
        command,
        bg_color,
        hover_color,
        fg_color="white",
        width=160,
        height=44,
        radius=22,
        font=("Segoe UI", 10, "bold"),
    ):
        super().__init__(
            parent, width=width, height=height, highlightthickness=0, bg="#f4f6f8"
        )
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text = text
        self.fg_color = fg_color
        self.width = width
        self.height = height
        self.radius = radius
        self.font = font

        self.rect = self.create_rounded_rect(0, 0, width, height, radius, fill=bg_color)
        self.text_id = self.create_text(
            width // 2, height // 2, text=text, fill=fg_color, font=font
        )

        self.bind("<Button-1>", lambda e: command())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def on_enter(self, e):
        self.itemconfig(self.rect, fill=self.hover_color)

    def on_leave(self, e):
        self.itemconfig(self.rect, fill=self.bg_color)


# ========================================
#           PDF COMPRESSION (ROBUST)
# ========================================
def compress_pdf_to_target(input_path, output_path, target_bytes, update_callback):
    best_file = None
    best_size = float("inf")
    log.info(f"Starting PDF compression → target ≤{target_bytes / (1024*1024):.2f} MB")

    total_qualities = len(range(95, 5, -10))
    quality_idx = 0

    for quality in range(95, 5, -10):
        quality_idx += 1
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
        try:
            reader = PdfReader(input_path)
            writer = PdfWriter()
            total_pages = len(reader.pages)
            processed = 0

            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    page.compress_content_streams()

                    if "/Resources" in page and "/XObject" in page["/Resources"]:
                        xobjects = page["/Resources"]["/XObject"]
                        xobj_dict = (
                            xobjects.get_object()
                            if hasattr(xobjects, "get_object")
                            else xobjects
                        )

                        for obj_name in list(xobj_dict.keys()):
                            obj = xobj_dict[obj_name]
                            if hasattr(obj, "get_object"):
                                obj = obj.get_object()

                            if obj.get("/Subtype") != "/Image":
                                continue

                            # === ROBUST IMAGE HANDLING ===
                            try:
                                data = obj.get_data()
                                if not data:
                                    continue  # Skip empty

                                # Try to open with PIL
                                img = Image.open(BytesIO(data))
                                if img.format not in ("JPEG", "PNG", "BMP", "TIFF"):
                                    log.debug(
                                        f"Skipping non-standard image format: {img.format}"
                                    )
                                    continue

                                if img.mode not in ("RGB", "L", "CMYK"):
                                    img = img.convert("RGB")

                                buf = BytesIO()
                                img.save(buf, "JPEG", quality=quality, optimize=True)
                                new_data = buf.getvalue()

                                # Replace with compressed
                                obj._data = new_data
                                obj.update(
                                    {
                                        NameObject("/Filter"): NameObject("/DCTDecode"),
                                        NameObject("/ColorSpace"): NameObject(
                                            "/DeviceRGB"
                                        ),
                                        NameObject("/BitsPerComponent"): NumberObject(
                                            8
                                        ),
                                        NameObject("/Length"): NumberObject(
                                            len(new_data)
                                        ),
                                    }
                                )
                                log.debug(
                                    f"Compressed {obj_name} → {len(new_data)/1024:.1f} KB"
                                )

                            except Exception as img_err:
                                # === FALLBACK: Keep original image ===
                                log.debug(
                                    f"Skipping uncompressible image {obj_name}: {img_err}"
                                )
                                # Do nothing → original image stays
                                pass

                    writer.add_page(page)
                    processed += 1
                    progress = 20 + (
                        70
                        * (quality_idx - 1 + processed / total_pages)
                        / total_qualities
                    )
                    update_callback(
                        int(progress),
                        f"Quality {quality} | Page {page_num}/{total_pages}",
                    )

                except Exception as page_err:
                    log.error(f"Page {page_num} error: {page_err}", exc_info=True)
                    writer.add_page(page)

            with open(temp, "wb") as f:
                writer.write(f)

            size = os.path.getsize(temp)
            log.info(f"Quality {quality}: {size / (1024*1024):.2f} MB")

            if size <= target_bytes:
                shutil.move(temp, output_path)
                update_callback(100, "Target Achieved!")
                log.info(f"Success at quality {quality}")
                return True, size

            if size < best_size:
                best_size = size
                if best_file:
                    os.unlink(best_file)
                best_file = temp
            else:
                os.unlink(temp)

        except Exception as e:
            log.error(f"Quality {quality} failed: {e}", exc_info=True)
            if os.path.exists(temp):
                os.unlink(temp)

    # Use best effort
    if best_file:
        shutil.move(best_file, output_path)
        update_callback(100, "Best Possible")
        log.info(f"Best: {best_size / (1024*1024):.2f} MB")
        return True, best_size

    update_callback(100, "No Improvement")
    return False, os.path.getsize(input_path)


# ========================================
#           OFFICE COMPRESSION
# ========================================
def compress_office_to_target(input_path, output_path, target_bytes, update_callback):
    best_file = None
    best_size = float("inf")
    ext = os.path.splitext(input_path)[1].lower()
    log.info(f"Compressing Office file: {input_path}")

    total_levels = 9
    for level in range(9, 0, -1):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=ext).name
        try:
            with zipfile.ZipFile(input_path, "r") as zin:
                with zipfile.ZipFile(
                    temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=level
                ) as zout:
                    items = zin.infolist()
                    for i, item in enumerate(items):
                        zout.writestr(item, zin.read(item.filename))
                        progress = (
                            20
                            + (70 * (10 - level) + 70 * i / len(items)) / total_levels
                        )
                        update_callback(int(progress), f"Zip Level {level}")

            size = os.path.getsize(temp)
            log.info(f"Level {level}: {size / (1024*1024):.2f} MB")

            if size <= target_bytes:
                shutil.move(temp, output_path)
                update_callback(100, "Completed!")
                return True, size

            if size < best_size:
                best_size = size
                if best_file:
                    os.unlink(best_file)
                best_file = temp
            else:
                os.unlink(temp)

        except Exception as e:
            log.error(f"Level {level} failed: {e}", exc_info=True)
            if os.path.exists(temp):
                os.unlink(temp)

    if best_file:
        shutil.move(best_file, output_path)
        update_callback(100, "Completed!")
        return True, best_size

    update_callback(100, "No improvement")
    return False, os.path.getsize(input_path)


# ========================================
#           POST-COMPRESSION POPUP
# ========================================
def show_completion_popup(input_path, output_path, original_mb, final_mb, saved_kb):
    popup = Toplevel(root)
    popup.title("Compression Complete!")
    popup.geometry("460x260")
    popup.resizable(False, False)
    popup.configure(bg="#f4f6f8")
    popup.grab_set()

    # Center popup
    popup.transient(root)
    popup.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() // 2) - (460 // 2)
    y = root.winfo_rooty() + (root.winfo_height() // 2) - (260 // 2)
    popup.geometry(f"+{x}+{y}")

    Label(
        popup,
        text="Success!",
        font=("Segoe UI", 16, "bold"),
        fg="#4CAF50",
        bg="#f4f6f8",
    ).pack(pady=(25, 10))

    info = f"{original_mb:.2f} MB → {final_mb:.2f} MB\nSaved: {saved_kb:.1f} KB"
    Label(popup, text=info, font=("Segoe UI", 11), fg="#333", bg="#f4f6f8").pack(pady=5)

    path_label = Label(
        popup,
        text=os.path.basename(output_path),
        font=("Segoe UI", 10, "italic"),
        fg="#1976D2",
        bg="#f4f6f8",
        cursor="hand2",
    )
    path_label.pack(pady=10)
    path_label.bind("<Button-1>", lambda e: os.startfile(output_path))

    btn_frame = Frame(popup, bg="#f4f6f8")
    btn_frame.pack(pady=20)

    def reset_app():
        selected_file.set("")
        file_label.config(text="(No file selected)", fg="#888")
        progress_bar["value"] = 0
        progress_label.config(text="Ready")
        popup.destroy()

    def open_and_reset():
        try:
            os.startfile(output_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")
        reset_app()

    RoundedButton(
        btn_frame,
        "Compress Another",
        lambda: [reset_app(), popup.destroy()],
        "#2196F3",
        "#1976D2",
        width=160,
    ).pack(side="left", padx=15)

    RoundedButton(
        btn_frame, "Open File", open_and_reset, "#4CAF50", "#388E3C", width=160
    ).pack(side="right", padx=15)

    popup.after(30000, popup.destroy)  # Auto-close after 30 sec


# ========================================
#              SETTINGS WINDOW (FIXED)
# ========================================
def open_settings():
    # Prevent duplicate windows
    for child in root.winfo_children():
        if isinstance(child, Toplevel) and child.title() == "Settings":
            child.lift()
            return

    win = Toplevel(root)
    win.title("Settings")
    win.geometry("420x400")
    win.resizable(False, False)
    win.configure(bg="#f4f6f8")
    win.grab_set()

    Label(
        win,
        text="Compression Settings",
        font=("Segoe UI", 14, "bold"),
        bg="#f4f6f8",
        fg="#1a1a1a",
    ).pack(pady=20)

    Radiobutton(
        win,
        text="By Percentage",
        variable=compression_mode,
        value=1,
        bg="#f4f6f8",
        font=("Segoe UI", 11),
    ).pack(anchor="w", padx=80)
    Radiobutton(
        win,
        text="By Target Size (MB)",
        variable=compression_mode,
        value=2,
        bg="#f4f6f8",
        font=("Segoe UI", 11),
    ).pack(anchor="w", padx=80, pady=(0, 15))

    input_frame = Frame(win, bg="#f4f6f8")
    input_frame.pack(pady=10, fill="x")

    rate_row = Frame(input_frame, bg="#f4f6f8")
    size_row = Frame(input_frame, bg="#f4f6f8")

    Label(
        rate_row, text="Compression Rate (%):", font=("Segoe UI", 10), bg="#f4f6f8"
    ).pack(side="left", padx=20)
    Entry(
        rate_row, textvariable=compression_rate, width=10, font=("Segoe UI", 10)
    ).pack(side="left", padx=10)

    Label(size_row, text="Target Size (MB):", font=("Segoe UI", 10), bg="#f4f6f8").pack(
        side="left", padx=20
    )
    Entry(size_row, textvariable=target_size, width=10, font=("Segoe UI", 10)).pack(
        side="left", padx=10
    )

    def update_fields(*args):
        rate_row.pack_forget()
        size_row.pack_forget()
        if compression_mode.get() == 1:
            rate_row.pack(pady=5, fill="x")
        else:
            size_row.pack(pady=5, fill="x")

    update_fields()
    compression_mode.trace("w", update_fields)

    Label(
        win,
        text="Small files (<1MB) use percentage automatically.",
        font=("Segoe UI", 9, "italic"),
        fg="#666",
        bg="#f4f6f8",
    ).pack(pady=15)
    RoundedButton(
        win, "Save Settings", win.destroy, "#2196F3", "#1976D2", width=180, height=44
    ).pack(pady=10)


# ========================================
#              OTHER WINDOWS
# ========================================
def open_about():
    win = Toplevel(root)
    win.title("About")
    win.geometry("400x260")
    win.configure(bg="#f4f6f8")
    win.grab_set()

    Label(
        win,
        text="Document Compressor",
        font=("Segoe UI", 16, "bold"),
        fg="#1976D2",
        bg="#f4f6f8",
    ).pack(pady=30)
    Label(
        win,
        text="Created by Jessie Albert J. Regualos",
        font=("Segoe UI", 11),
        bg="#f4f6f8",
    ).pack()
    Label(
        win,
        text="IT Specialist - CDO and Butuan",
        font=("Segoe UI", 10),
        fg="#555",
        bg="#f4f6f8",
    ).pack(pady=10)
    RoundedButton(
        win, "Close", win.destroy, "#E53935", "#C62828", width=120, height=40
    ).pack(pady=15)


# ========================================
#              FILE SELECTION
# ========================================
def select_file():
    path = filedialog.askopenfilename(
        filetypes=[
            ("Documents", "*.pdf *.docx *.xlsx"),
            ("PDF", "*.pdf"),
            ("Word", "*.docx"),
            ("Excel", "*.xlsx"),
        ]
    )
    if path:
        selected_file.set(path)
        file_label.config(text=os.path.basename(path), fg="#1a1a1a")
        log.info(f"File selected: {path}")


# ========================================
#              COMPRESSION LOGIC
# ========================================
def start_compression():
    if not selected_file.get():
        messagebox.showwarning("No File", "Please select a file!")
        return

    input_path = selected_file.get()
    ext = os.path.splitext(input_path)[1].lower()
    if ext not in [".pdf", ".docx", ".xlsx"]:
        messagebox.showerror("Error", "Unsupported file!")
        log.error(f"Unsupported file: {ext}")
        return

    dir_name = os.path.dirname(input_path)
    base_name = os.path.basename(input_path)
    name, _ = os.path.splitext(base_name)
    default_name = f"{name}_compressed{ext}"
    default_path = os.path.join(dir_name, default_name)

    output_path = filedialog.asksaveasfilename(
        initialfile=default_name,
        initialdir=dir_name,
        defaultextension=ext,
        filetypes=[(ext[1:].upper(), f"*{ext}")],
    )
    if not output_path:
        return

    log.info(f"Starting compression: {input_path} → {output_path}")
    threading.Thread(
        target=compress_file, args=(input_path, output_path), daemon=True
    ).start()


def compress_file(input_path, output_path):
    def update(pct, txt):
        progress_bar["value"] = pct
        progress_label.config(text=txt)
        root.update_idletasks()

    compress_button.config(state="disabled")
    browse_button.config(state="disabled")
    update(0, "Analyzing...")

    try:
        original_size = os.path.getsize(input_path)
        original_mb = original_size / (1024 * 1024)
        ext = os.path.splitext(input_path)[1].lower()

        if original_mb < 1 or compression_mode.get() == 1:
            rate = max(10, min(95, compression_rate.get()))
            target_bytes = original_size * (100 - rate) / 100
            update(10, f"Target: {rate}% reduction")
            log.info(f"Percentage mode: {rate}% → {target_bytes / (1024*1024):.2f} MB")
        else:
            target_mb = max(0.1, target_size.get())
            target_bytes = target_mb * 1024 * 1024
            update(10, f"Target: ≤{target_mb:.2f} MB")
            log.info(f"Target size: {target_mb:.2f} MB")

        update(20, "Compressing...")

        if ext == ".pdf":
            success, final_size = compress_pdf_to_target(
                input_path, output_path, target_bytes, update
            )
        else:
            success, final_size = compress_office_to_target(
                input_path, output_path, target_bytes, update
            )

        final_mb = final_size / (1024 * 1024)
        saved_kb = (original_size - final_size) / 1024

        if success and final_size < original_size * 0.9:
            root.after(
                0,
                show_completion_popup,
                input_path,
                output_path,
                original_mb,
                final_mb,
                saved_kb,
            )
            log.info(f"Success: {original_mb:.2f} → {final_mb:.2f} MB")
        else:
            root.after(
                0,
                lambda: messagebox.showinfo(
                    "Already Optimized", "No further compression possible."
                ),
            )
            log.info("No improvement.")

    except Exception as e:
        root.after(
            0, lambda: messagebox.showerror("Error", f"Compression failed:\n{e}")
        )
        log.error("Compression failed", exc_info=True)
        update(0, "Failed")
    finally:
        compress_button.config(state="normal")
        browse_button.config(state="normal")


# ========================================
#               MAIN GUI
# ========================================
root = Tk()
root.title("Document Compressor")
root.geometry("540x480")
root.resizable(False, False)
root.configure(bg="#f4f6f8")

selected_file = StringVar()
compression_mode = IntVar(value=1)
compression_rate = IntVar(value=75)
target_size = DoubleVar(value=2.0)

menu = Menu(root)
menu.add_command(label="Settings", command=open_settings)
menu.add_command(label="About", command=open_about)
menu.add_separator()
menu.add_command(label="Exit", command=root.quit)
root.config(menu=menu)

Frame(root, bg="#1976D2", height=80).pack(fill="x")
Label(
    root,
    text="Document Compressor",
    font=("Segoe UI", 20, "bold"),
    fg="white",
    bg="#1976D2",
).pack(pady=20)

Label(root, text="Selected File:", font=("Segoe UI", 11), bg="#f4f6f8").pack(
    pady=(20, 5)
)
file_label = Label(
    root,
    text="(No file selected)",
    font=("Segoe UI", 10),
    bg="white",
    fg="#888",
    relief="solid",
    bd=1,
    padx=15,
    pady=12,
    width=60,
)
file_label.pack(pady=5)

btn_frame = Frame(root, bg="#f4f6f8")
btn_frame.pack(pady=25)

browse_button = RoundedButton(
    btn_frame, "Browse File", select_file, "#2196F3", "#1976D2"
)
browse_button.pack(side="left", padx=25)

compress_button = RoundedButton(
    btn_frame, "Compress & Save", start_compression, "#4CAF50", "#388E3C", width=200
)
compress_button.pack(side="right", padx=25)

style = ttk.Style()
style.theme_use("clam")
style.configure(
    "TProgressbar", thickness=28, background="#4CAF50", troughcolor="#e0e0e0"
)
progress_bar = ttk.Progressbar(
    root, length=440, style="TProgressbar", mode="determinate"
)
progress_bar.pack(pady=25)

progress_label = Label(
    root, text="Ready", font=("Segoe UI", 11, "bold"), fg="#333", bg="#f4f6f8"
)
progress_label.pack()

Label(
    root,
    text="Supports: PDF • DOCX • XLSX",
    font=("Segoe UI", 9, "italic"),
    fg="#777",
    bg="#f4f6f8",
).pack(side="bottom", pady=20)

log.info("Document Compressor started.")
root.mainloop()
