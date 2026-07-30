import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Pixel Workbench")
    parser.add_argument('--script', type=str, help='Path to a DSL script to execute headlessly')
    parser.add_argument('diff_args', nargs='*', help='For diffing: diff old.png new.png [--json report.json] [--image diff.png]')

    args, unknown = parser.parse_known_args()

    if args.diff_args and args.diff_args[0] == "diff":
        from .tools.compare import compare_files

        diff_parser = argparse.ArgumentParser(prog="pixel-workbench diff")
        diff_parser.add_argument('old', type=str)
        diff_parser.add_argument('new', type=str)
        diff_parser.add_argument('--json', type=str)
        diff_parser.add_argument('--image', type=str)

        diff_args = diff_parser.parse_args(args.diff_args[1:] + unknown)
        compare_files(diff_args.old, diff_args.new, diff_args.image, diff_args.json)
        sys.exit(0)

    if args.script:
        from .app import Workbench
        from .scripting.interpreter import Interpreter

        wb = Workbench()
        interpreter = Interpreter(wb)
        with open(args.script, 'r') as f:
            interpreter.execute_script(f.read())
        sys.exit(0)

    # Otherwise, launch GUI
    try:
        from .gui.main_window import run_gui
        run_gui()
    except ImportError as e:
        print(f"Failed to load GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
