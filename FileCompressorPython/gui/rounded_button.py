# gui/rounded_button.py
from tkinter import Canvas


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
            parent, width=width, height=height, highlightthickness=0, bg="#1e1e1e"
        )
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color

        self.rect = self.create_rounded_rect(0, 0, width, height, radius, fill=bg_color)
        self.text_id = self.create_text(
            width // 2, height // 2, text=text, fill=fg_color, font=font
        )

        self.bind("<Button-1>", lambda e: command())
        self.bind("<Enter>", lambda e: self.itemconfig(self.rect, fill=hover_color))
        self.bind("<Leave>", lambda e: self.itemconfig(self.rect, fill=bg_color))

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kw):
        points = [
            x1 + r,
            y1,
            x2 - r,
            y1,
            x2,
            y1,
            x2,
            y1 + r,
            x2,
            y2 - r,
            x2,
            y2,
            x2 - r,
            y2,
            x1 + r,
            y2,
            x1,
            y2,
            x1,
            y2 - r,
            x1,
            y1 + r,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kw)
