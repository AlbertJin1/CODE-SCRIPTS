# gui/about_window.py
from tkinter import Toplevel, Label
from .rounded_button import RoundedButton


def open_about(root):
    win = Toplevel(root)
    win.title("About")
    win.geometry("400x260")
    win.configure(bg="#1e1e1e")
    win.grab_set()

    Label(
        win,
        text="CompressMaster",
        font=("Segoe UI", 16, "bold"),
        fg="#4FC3F7",
        bg="#1e1e1e",
    ).pack(pady=30)
    Label(
        win, text="Created by Jessie Albert J. Regualos", fg="#ccc", bg="#1e1e1e"
    ).pack()
    Label(win, text="IT Specialist - CDO & Butuan", fg="#888", bg="#1e1e1e").pack(
        pady=10
    )
    RoundedButton(win, "Close", win.destroy, "#E53935", "#C62828", width=120).pack(
        pady=15
    )
