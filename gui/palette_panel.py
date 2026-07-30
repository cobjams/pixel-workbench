import tkinter as tk
from ..core.palette import PaletteOperations

class PalettePanel(tk.Frame):
    def __init__(self, parent, workbench, canvas, **kwargs):
        super().__init__(parent, **kwargs)
        self.workbench = workbench
        self.canvas = canvas

        self.label = tk.Label(self, text="Palette")
        self.label.pack(side=tk.TOP, fill=tk.X)

        self.color_frame = tk.Frame(self)
        self.color_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.color_btns = []

    def refresh(self):
        # Clear existing
        for btn in self.color_btns:
            btn.destroy()
        self.color_btns.clear()

        doc = self.workbench.document
        if not doc.image or doc.mode != 'P':
            self.label.config(text="Palette (Not P mode)")
            return

        colors = PaletteOperations.get_palette_colors(doc.image)
        if not colors:
            return

        # Only show up to max used index for neatness, or first 256
        # Let's show first 16 for a simple view, or a grid
        self.label.config(text=f"Palette (P Mode)")

        # Determine how many colors to show (avoid 256 empty ones)
        # We will show up to 256, but in a wrapped grid
        for i, c in enumerate(colors[:256]):
            # Skip trailing blacks if it's just padding, but we don't know for sure
            # We'll just display a grid 16x16

            hex_c = f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"

            btn = tk.Button(self.color_frame, bg=hex_c, width=2, height=1)
            btn.grid(row=i//16, column=i%16, padx=1, pady=1)

            # Left click to select color
            btn.bind("<Button-1>", lambda e, idx=i: self.select_color(idx))

            self.color_btns.append(btn)

    def select_color(self, idx):
        self.canvas.selected_color = idx
        print(f"Selected palette index: {idx}")
