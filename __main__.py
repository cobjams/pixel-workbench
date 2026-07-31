import sys
import argparse

import json

def main():
    parser = argparse.ArgumentParser(description="Pixel Workbench")
    parser.add_argument('--script', type=str, help='Path to a DSL script to execute headlessly')
    parser.add_argument('subcommand_args', nargs='*', help='Subcommands: diff, ai')

    args, unknown = parser.parse_known_args()

    if args.subcommand_args and args.subcommand_args[0] == "ai":
        from .app import Workbench
        wb = Workbench()

        ai_parser = argparse.ArgumentParser(prog="pixel-workbench ai")
        ai_subparsers = ai_parser.add_subparsers(dest="command")

        gen_parser = ai_subparsers.add_parser("generate")
        gen_parser.add_argument("--prompt", type=str, required=True)
        gen_parser.add_argument("--size", type=str, default="16x16")
        gen_parser.add_argument("--style-reference", type=str)
        gen_parser.add_argument("--palette-reference", type=str)
        gen_parser.add_argument("--output", type=str)

        style_parser = ai_subparsers.add_parser("analyze-style")
        style_parser.add_argument("path", type=str)

        review_parser = ai_subparsers.add_parser("review")
        review_parser.add_argument("path", type=str)

        ai_args = ai_parser.parse_args(args.subcommand_args[1:] + unknown)

        if ai_args.command == "generate":
            size_parts = ai_args.size.lower().split("x")
            size = (int(size_parts[0]), int(size_parts[1]))

            draft = wb.ai.generate_sprite(
                prompt=ai_args.prompt,
                size=size,
                style_reference=ai_args.style_reference,
                palette_reference=ai_args.palette_reference
            )

            report = wb.ai.review_sprite(draft)

            if ai_args.output:
                draft.document.save(ai_args.output)

            print(json.dumps(draft.to_dict(), indent=2))

        elif ai_args.command == "analyze-style":
            result = wb.ai.analyze_style(ai_args.path)
            print(json.dumps(result, indent=2))

        elif ai_args.command == "review":
            # For CLI review of a saved image, we open it first
            wb.open(ai_args.path)
            from .ai.draft import SpriteDraft
            draft = SpriteDraft(wb.document)
            result = wb.ai.review_sprite(draft)
            print(json.dumps(result, indent=2))

        sys.exit(0)

    if args.subcommand_args and args.subcommand_args[0] == "diff":
        from .tools.compare import compare_files

        diff_parser = argparse.ArgumentParser(prog="pixel-workbench diff")
        diff_parser.add_argument('old', type=str)
        diff_parser.add_argument('new', type=str)
        diff_parser.add_argument('--json', type=str)
        diff_parser.add_argument('--image', type=str)

        diff_args = diff_parser.parse_args(args.subcommand_args[1:] + unknown)
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
