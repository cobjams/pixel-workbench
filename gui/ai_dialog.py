import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import ImageTk

class AIDraftPreviewDialog(tk.Toplevel):
    def __init__(self, parent, workbench, draft):
        super().__init__(parent)
        self.title("AI Draft Preview")
        self.geometry("400x500")
        self.workbench = workbench
        self.draft = draft
        self.accepted = False

        self.transient(parent)
        self.grab_set()

        # Display metadata
        tk.Label(self, text="Prompt:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        tk.Label(self, text=draft.prompt, wraplength=380, justify="left").pack(anchor="w", padx=10)

        # Run review to get score and warnings
        report = workbench.ai.review_sprite(draft)
        score_text = f"Style Match: {report.get('style_match_score', 0)} / 1.0"
        tk.Label(self, text=score_text, font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))

        if report.get("warnings"):
            tk.Label(self, text="Warnings:", fg="red").pack(anchor="w", padx=10)
            for w in report["warnings"]:
                tk.Label(self, text=f"- {w}", fg="red").pack(anchor="w", padx=20)
        else:
            tk.Label(self, text="Validation Passed", fg="green").pack(anchor="w", padx=10)

        # Display Image
        self.img_frame = tk.Frame(self, bg="#444", width=200, height=200)
        self.img_frame.pack(pady=20)

        # Scale up image for visibility
        if draft.document.image:
            img = draft.document.image.copy()
            # Scale 8x
            scaled = img.resize((img.width * 8, img.height * 8), resample=0)
            self.tk_image = ImageTk.PhotoImage(scaled)
            tk.Label(self.img_frame, image=self.tk_image, bg="#444").pack()
        else:
            tk.Label(self.img_frame, text="No Image", fg="white", bg="#444").pack(fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(side=tk.BOTTOM, pady=20)

        tk.Button(btn_frame, text="Accept", command=self.accept, bg="green", fg="white", width=10).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Discard", command=self.discard, bg="red", fg="white", width=10).pack(side=tk.LEFT, padx=10)

    def accept(self):
        self.accepted = True
        self.destroy()

    def discard(self):
        self.accepted = False
        self.destroy()

def show_generate_dialog(parent, workbench):
    prompt = simpledialog.askstring("Generate AI Sprite", "Enter prompt:", parent=parent)
    if prompt:
        try:
            draft = workbench.ai.generate_sprite(prompt=prompt, size=(16, 16))
            dialog = AIDraftPreviewDialog(parent, workbench, draft)
            parent.wait_window(dialog)
            if dialog.accepted:
                workbench.open_document(draft.document)
                return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate sprite: {e}")
    return False
