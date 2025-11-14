# gui/settings_window.py
from tkinter import Toplevel, Label, Radiobutton, Entry, Frame
from .rounded_button import RoundedButton


def open_settings(root, compression_mode, compression_rate, target_size):
    for child in root.winfo_children():
        if isinstance(child, Toplevel) and child.title() == "Settings":
            child.lift()
            return

    win = Toplevel(root)
    win.title("Settings")
    win.geometry("420x400")
    win.configure(bg="#1e1e1e")
    win.grab_set()

    Label(
        win,
        text="Compression Settings",
        font=("Segoe UI", 14, "bold"),
        fg="white",
        bg="#1e1e1e",
    ).pack(pady=20)

    Radiobutton(
        win,
        text="By Percentage",
        variable=compression_mode,
        value=1,
        bg="#1e1e1e",
        fg="white",
        selectcolor="#333",
    ).pack(anchor="w", padx=80)
    Radiobutton(
        win,
        text="By Target Size (MB)",
        variable=compression_mode,
        value=2,
        bg="#1e1e1e",
        fg="white",
        selectcolor="#333",
    ).pack(anchor="w", padx=80, pady=(0, 15))

    input_frame = Frame(win, bg="#1e1e1e")
    input_frame.pack(pady=10, fill="x")

    rate_row = Frame(input_frame, bg="#1e1e1e")
    size_row = Frame(input_frame, bg="#1e1e1e")

    Label(rate_row, text="Rate (%):", fg="white", bg="#1e1e1e").pack(
        side="left", padx=20
    )
    Entry(
        rate_row,
        textvariable=compression_rate,
        width=10,
        bg="#333",
        fg="white",
        insertbackground="white",
    ).pack(side="left", padx=10)

    Label(size_row, text="Target (MB):", fg="white", bg="#1e1e1e").pack(
        side="left", padx=20
    )
    Entry(
        size_row,
        textvariable=target_size,
        width=10,
        bg="#333",
        fg="white",
        insertbackground="white",
    ).pack(side="left", padx=10)

    def update(*args):
        rate_row.pack_forget()
        size_row.pack_forget()
        (rate_row if compression_mode.get() == 1 else size_row).pack(pady=5, fill="x")

    update()
    compression_mode.trace("w", update)

    Label(
        win,
        text="Small files (<1MB) use %",
        fg="#888",
        bg="#1e1e1e",
        font=("Segoe UI", 9, "italic"),
    ).pack(pady=15)
    RoundedButton(win, "Save", win.destroy, "#2196F3", "#1976D2", width=180).pack(
        pady=10
    )
