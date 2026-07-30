import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import ImageTk

class PixelCanvas(tk.Canvas):
    def __init__(self, parent, workbench, **kwargs):
        super().__init__(parent, **kwargs)
        self.workbench = workbench
        self.zoom_level = 8
        self.pan_x = 0
        self.pan_y = 0
        self.tk_image = None

        self.bind("<Button-1>", self.on_left_click)
        self.bind("<B1-Motion>", self.on_left_drag)
        self.bind("<Button-3>", self.on_right_click)

        self.bind("<MouseWheel>", self.on_mouse_wheel)
        self.bind("<Button-4>", self.on_mouse_wheel) # Linux scroll up
        self.bind("<Button-5>", self.on_mouse_wheel) # Linux scroll down

        self.bind("<Configure>", self.on_resize)

        # Tools could be extracted later. For now, simple modes
        self.current_tool = "pencil"
        self.selected_color = None # Set correctly upon loading or eyedropper

    def redraw(self):
        self.delete("all")
        if not self.workbench.document.image:
            return

        img = self.workbench.document.image

        # We need an RGBA copy for Tkinter display to handle transparency nicely
        # But we DO NOT modify the underlying document mode.
        display_img = img.convert("RGBA")

        # Nearest neighbor scaling
        w, h = display_img.size
        scaled_img = display_img.resize((w * self.zoom_level, h * self.zoom_level), resample=0)

        self.tk_image = ImageTk.PhotoImage(scaled_img)

        # Draw image
        self.create_image(self.pan_x, self.pan_y, image=self.tk_image, anchor=tk.NW)

        # Draw pixel grid if zoomed enough
        if self.zoom_level >= 4:
            self._draw_grid(w, h)

    def _draw_grid(self, w, h):
        for x in range(w + 1):
            cx = self.pan_x + x * self.zoom_level
            self.create_line(cx, self.pan_y, cx, self.pan_y + h * self.zoom_level, fill="#444", stipple="gray50")
        for y in range(h + 1):
            cy = self.pan_y + y * self.zoom_level
            self.create_line(self.pan_x, cy, self.pan_x + w * self.zoom_level, cy, fill="#444", stipple="gray50")

    def on_mouse_wheel(self, event):
        # Zoom in/out based on scroll direction
        if event.num == 4 or event.delta > 0:
            self.zoom_level = min(self.zoom_level * 2, 64)
        elif event.num == 5 or event.delta < 0:
            self.zoom_level = max(self.zoom_level // 2, 1)
        self.redraw()

    def on_resize(self, event):
        self.redraw()

    def _get_pixel_coords(self, event):
        px = (event.x - self.pan_x) // self.zoom_level
        py = (event.y - self.pan_y) // self.zoom_level
        return px, py

    def _paint(self, event):
        if not self.workbench.document.image:
            return

        if self.selected_color is None:
            # Set default color if none selected yet
            if self.workbench.document.mode == 'P':
                self.selected_color = 1
            else:
                self.selected_color = (255, 255, 255, 255)

        px, py = self._get_pixel_coords(event)

        w, h = self.workbench.document.image.size
        if 0 <= px < w and 0 <= py < h:
            mode = self.workbench.document.mode
            try:
                if mode == 'P':
                    # Assuming selected_color is an index
                    self.workbench.paint_index(px, py, int(self.selected_color))
                else:
                    self.workbench.paint_color(px, py, self.selected_color)
                self.redraw()

                # Notify parent to update palette if it changed
                self.event_generate("<<ImageChanged>>")
            except Exception as e:
                print(f"Paint error: {e}")

    def on_left_click(self, event):
        if self.current_tool == "pencil":
            self._paint(event)

    def on_left_drag(self, event):
        if self.current_tool == "pencil":
            # Just push state manually for single strokes, or group them
            # For simplicity, each drag pixel might be a separate action,
            # but ideally you'd group them. For now we will just paint.
            self._paint(event)

    def on_right_click(self, event):
        if not self.workbench.document.image:
            return

        # Eyedropper
        px, py = self._get_pixel_coords(event)
        w, h = self.workbench.document.image.size
        if 0 <= px < w and 0 <= py < h:
            val = self.workbench.document.image.getpixel((px, py))
            self.selected_color = val
            print(f"Eyedropper picked: {val}")
