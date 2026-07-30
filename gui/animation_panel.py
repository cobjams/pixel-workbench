import tkinter as tk
from PIL import ImageTk

class AnimationPanel(tk.Frame):
    def __init__(self, parent, workbench, **kwargs):
        super().__init__(parent, **kwargs)
        self.workbench = workbench

        self.label = tk.Label(self, text="Animation Preview")
        self.label.pack(side=tk.TOP, fill=tk.X)

        controls = tk.Frame(self)
        controls.pack(side=tk.TOP, fill=tk.X)

        tk.Label(controls, text="W:").pack(side=tk.LEFT)
        self.fw_var = tk.StringVar(value="16")
        tk.Entry(controls, textvariable=self.fw_var, width=3).pack(side=tk.LEFT)

        tk.Label(controls, text="H:").pack(side=tk.LEFT)
        self.fh_var = tk.StringVar(value="15")
        tk.Entry(controls, textvariable=self.fh_var, width=3).pack(side=tk.LEFT)

        tk.Button(controls, text="Play", command=self.play).pack(side=tk.LEFT)
        tk.Button(controls, text="Stop", command=self.stop).pack(side=tk.LEFT)

        self.preview_canvas = tk.Canvas(self, width=64, height=64, bg="#555")
        self.preview_canvas.pack(pady=5)

        self.frames = []
        self.current_frame = 0
        self.playing = False
        self.tk_image = None
        self.zoom = 4

    def slice_sheet(self):
        doc = self.workbench.document
        if not doc.image:
            return []

        try:
            fw = int(self.fw_var.get())
            fh = int(self.fh_var.get())
        except ValueError:
            return []

        img = doc.image.convert("RGBA")
        w, h = img.size

        frames = []
        # Basic slice: left to right, top to bottom
        for y in range(0, h, fh):
            for x in range(0, w, fw):
                if x + fw <= w and y + fh <= h:
                    frame = img.crop((x, y, x + fw, y + fh))
                    # Scale it
                    frame = frame.resize((fw * self.zoom, fh * self.zoom), resample=0)
                    frames.append(ImageTk.PhotoImage(frame))

        return frames

    def play(self):
        self.frames = self.slice_sheet()
        if not self.frames:
            return

        self.playing = True
        self.current_frame = 0
        self.animate()

    def stop(self):
        self.playing = False

    def animate(self):
        if not self.playing or not self.frames:
            return

        self.preview_canvas.delete("all")
        self.tk_image = self.frames[self.current_frame]
        self.preview_canvas.create_image(32, 32, image=self.tk_image, anchor=tk.CENTER)

        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self.after(200, self.animate) # 5 fps
