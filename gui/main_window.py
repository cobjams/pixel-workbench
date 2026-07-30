import tkinter as tk
from tkinter import filedialog, messagebox
from ..app import Workbench
from .canvas import PixelCanvas
from .palette_panel import PalettePanel

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Workbench")
        self.geometry("1024x768")

        self.workbench = Workbench()

        # Menu
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self.undo)
        edit_menu.add_command(label="Redo", command=self.redo)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Main Layout
        self.left_panel = tk.Frame(self, width=200, bg="#ddd")
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)

        self.center_panel = tk.Frame(self, bg="#333")
        self.center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = PixelCanvas(self.center_panel, self.workbench, bg="#222")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<<ImageChanged>>", self.on_image_changed)

        self.palette_panel = PalettePanel(self.left_panel, self.workbench, self.canvas)
        self.palette_panel.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        from .animation_panel import AnimationPanel
        self.animation_panel = AnimationPanel(self.left_panel, self.workbench)
        self.animation_panel.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        from .asset_browser import AssetBrowser
        self.asset_browser = AssetBrowser(self.left_panel, self)
        self.asset_browser.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

    def open_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.bmp"), ("All files", "*.*")]
        )
        if filepath:
            try:
                self.workbench.open(filepath)
                self.refresh_ui()
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")

    def save_file(self):
        if not self.workbench.document.filepath:
            filepath = filedialog.asksaveasfilename(defaultextension=".png")
            if not filepath:
                return
        else:
            filepath = self.workbench.document.filepath

        try:
            self.workbench.save(filepath)
            messagebox.showinfo("Saved", f"Saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {e}")

    def undo(self):
        if self.workbench.undo():
            self.refresh_ui()

    def redo(self):
        if self.workbench.redo():
            self.refresh_ui()

    def on_image_changed(self, event):
        self.palette_panel.refresh()

    def refresh_ui(self):
        self.canvas.redraw()
        self.palette_panel.refresh()

def run_gui():
    app = MainWindow()
    app.mainloop()
