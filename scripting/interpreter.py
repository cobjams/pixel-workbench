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
        elif cmd == "undo":
            self.workbench.undo()
        elif cmd == "redo":
            self.workbench.redo()
        elif cmd == "validate":
            result = self.workbench.validate()
            print(result.to_dict())
        else:
            raise ValueError(f"Unknown command: {cmd}")
