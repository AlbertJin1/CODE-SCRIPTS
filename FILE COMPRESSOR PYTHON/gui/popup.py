# gui/popup.py
from tkinter import Toplevel, Label, Frame
from .rounded_button import RoundedButton
import os


def show_completion_popup(
    root, input_path, output_path, original_mb, final_mb, saved_kb, reset_callback
):
    popup = Toplevel(root)
    popup.title("Compression Complete!")
    popup.geometry("460x260")
    popup.resizable(False, False)
    popup.configure(bg="#1e1e1e")
    popup.grab_set()

    x = root.winfo_rootx() + (root.winfo_width() // 2) - 230
    y = root.winfo_rooty() + (root.winfo_height() // 2) - 130
    popup.geometry(f"+{x}+{y}")

    Label(
        popup,
        text="Success!",
        font=("Segoe UI", 16, "bold"),
        fg="#4CAF50",
        bg="#1e1e1e",
    ).pack(pady=(25, 10))
    Label(
        popup,
        text=f"{original_mb:.2f} → {final_mb:.2f} MB\nSaved: {saved_kb:.1f} KB",
        fg="#ddd",
        bg="#1e1e1e",
    ).pack(pady=5)

    path_lbl = Label(
        popup,
        text=os.path.basename(output_path),
        fg="#4FC3F7",
        bg="#1e1e1e",
        cursor="hand2",
        font=("Segoe UI", 10, "italic"),
    )
    path_lbl.pack(pady=10)
    path_lbl.bind("<Button-1>", lambda e: os.startfile(output_path))

    btns = Frame(popup, bg="#1e1e1e")
    btns.pack(pady=20)

    RoundedButton(
        btns,
        "Compress Another",
        lambda: [reset_callback(), popup.destroy()],
        "#2196F3",
        "#1976D2",
    ).pack(side="left", padx=15)
    RoundedButton(
        btns,
        "Open File",
        lambda: [os.startfile(output_path), reset_callback(), popup.destroy()],
        "#4CAF50",
        "#388E3C",
    ).pack(side="right", padx=15)

    popup.after(30000, popup.destroy)
