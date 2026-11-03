import sys
import shlex

class Interpreter:
    def __init__(self, workbench):
        self.workbench = workbench

    def execute_script(self, script_text):
        for line_no, line in enumerate(script_text.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            try:
                self.execute_command(line)
            except Exception as e:
                print(f"Error on line {line_no}: '{line}' -> {e}", file=sys.stderr)
                raise

    def execute_command(self, line):
        tokens = shlex.split(line)
        if not tokens:
            return

        cmd = tokens[0].lower()
        args = tokens[1:]

        if cmd == "open":
            self.workbench.open(args[0])
        elif cmd == "new":
            from PIL import Image
            w = int(args[0])
            h = int(args[1])
            mode = args[2] if len(args) > 2 else "RGBA"
            bg = 0 if mode == "P" else ((0, 0, 0, 0) if mode == "RGBA" else (0, 0, 0))
            self.workbench.document.image = Image.new(mode, (w, h), bg)
            self.workbench.document.original_mode = mode
        elif cmd == "save":
            filepath = args[0] if args else None
            self.workbench.save(filepath)
        elif cmd == "paint_index":
            self.workbench.paint_index(int(args[0]), int(args[1]), int(args[2]))
        elif cmd == "paint_color" or cmd == "paint_rgb":
            self.workbench.paint_color(int(args[0]), int(args[1]), args[2])
        elif cmd == "replace_index":
            self.workbench.replace_index(int(args[0]), int(args[1]))
        elif cmd == "replace_color":
            self.workbench.replace_color(args[0], args[1])
        elif cmd == "mirror":
            self.workbench.mirror(args[0])
        elif cmd == "crop":
            self.workbench.crop(int(args[0]), int(args[1]), int(args[2]), int(args[3]))
        elif cmd == "resize_canvas":
            self.workbench.resize_canvas(int(args[0]), int(args[1]))
        elif cmd == "draw_line":
            self.workbench.draw_line(int(args[0]), int(args[1]), int(args[2]), int(args[3]), args[4])
        elif cmd == "draw_rect":
            fill = args[5].lower() != "false" if len(args) > 5 else True
            self.workbench.draw_rect(int(args[0]), int(args[1]), int(args[2]), int(args[3]), args[4], fill=fill)
        elif cmd == "draw_ellipse":
            fill = args[5].lower() != "false" if len(args) > 5 else True
            self.workbench.draw_ellipse(int(args[0]), int(args[1]), int(args[2]), int(args[3]), args[4], fill=fill)
        elif cmd == "flood_fill":
            self.workbench.flood_fill(int(args[0]), int(args[1]), args[2])
        elif cmd == "generate_outline":
            color = args[0] if len(args) > 0 else "#000000"
            mode = args[1] if len(args) > 1 else "outside"
            self.workbench.generate_outline(color=color, mode=mode)
        elif cmd == "apply_shading":
            light_dir = args[0] if len(args) > 0 else "top_left"
            intensity = float(args[1]) if len(args) > 1 else 0.22
            self.workbench.apply_shading(light_dir=light_dir, intensity=intensity)
        elif cmd == "repair":
            self.workbench.repair()
        elif cmd == "undo":
            self.workbench.undo()
        elif cmd == "redo":
            self.workbench.redo()
        elif cmd == "validate":
            result = self.workbench.validate()
            print(result.to_dict())
        else:
            raise ValueError(f"Unknown command: {cmd}")
