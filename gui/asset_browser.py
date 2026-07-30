import tkinter as tk
import os

class AssetBrowser(tk.Frame):
    def __init__(self, parent, main_window, **kwargs):
        super().__init__(parent, **kwargs)
        self.main_window = main_window

        self.label = tk.Label(self, text="Assets")
        self.label.pack(side=tk.TOP, fill=tk.X)

        self.listbox = tk.Listbox(self)
        self.listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.listbox.bind("<Double-Button-1>", self.on_double_click)

        self.assets = []
        self.scan_assets()

    def scan_assets(self):
        # Auto-detect core/src/main/assets if it exists in CWD
        base_dir = os.path.join(os.getcwd(), "core", "src", "main", "assets")
        if not os.path.exists(base_dir):
            base_dir = os.getcwd() # Fallback

        self.assets.clear()
        self.listbox.delete(0, tk.END)

        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.lower().endswith(('.png', '.bmp')):
                    path = os.path.join(root, file)
                    rel_path = os.path.relpath(path, base_dir)
                    self.assets.append(path)
                    self.listbox.insert(tk.END, rel_path)

    def on_double_click(self, event):
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            path = self.assets[idx]
            try:
                self.main_window.workbench.open(path)
                self.main_window.refresh_ui()
            except Exception as e:
                print(f"Error opening asset: {e}")
