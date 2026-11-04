import sys
import argparse

import json

def main():
    parser = argparse.ArgumentParser(description="Pixel Workbench")
    parser.add_argument('--script', type=str, help='Path to a DSL script to execute headlessly')
    parser.add_argument('subcommand_args', nargs='*', help='Subcommands: diff, construct, analyze, review, repair, grid, regression, mcp-tools, mcp-serve, call-tool')

    args, unknown = parser.parse_known_args()

    if args.subcommand_args:
        subcommand = args.subcommand_args[0]

        if subcommand in ("construct", "analyze", "review", "repair", "grid", "regression", "mcp-tools", "mcp-serve", "call-tool"):
            if subcommand == "mcp-tools":
                from .tools.mcp_server import AgentToolServer
                server = AgentToolServer()
                print(json.dumps(server.get_tool_schemas(), indent=2))
                sys.exit(0)

            if subcommand == "mcp-serve":
                from .tools.mcp_server import AgentToolServer
                server = AgentToolServer()
                server.serve_stdio()
                sys.exit(0)

            if subcommand == "call-tool":
                from .tools.mcp_server import AgentToolServer
                tool_parser = argparse.ArgumentParser(prog="pixel-workbench call-tool")
                tool_parser.add_argument("name", type=str)
                tool_parser.add_argument("--args", type=str, default="{}")
                tool_args = tool_parser.parse_args(args.subcommand_args[1:] + unknown)
                server = AgentToolServer()
                result = server.call_tool(tool_args.name, json.loads(tool_args.args))
                print(json.dumps(result, indent=2))
                sys.exit(0)

            from .app import Workbench
            wb = Workbench()

            cmd_parser = argparse.ArgumentParser(prog=f"pixel-workbench {subcommand}")

            if subcommand == "construct":
                cmd_parser.add_argument("--prompt", type=str, required=True)
                cmd_parser.add_argument("--size", type=str, default="16x16")
                cmd_parser.add_argument("--style-reference", type=str)
                cmd_parser.add_argument("--palette-reference", type=str)
                cmd_parser.add_argument("--output", type=str)

                cmd_args = cmd_parser.parse_args(args.subcommand_args[1:] + unknown)
                size_parts = cmd_args.size.lower().split("x")
                size = (int(size_parts[0]), int(size_parts[1]))

                draft = wb.construct(
                    prompt=cmd_args.prompt,
                    size=size,
                    style_reference=cmd_args.style_reference,
                    palette_reference=cmd_args.palette_reference
                )

                report = wb.review(draft)

                if cmd_args.output:
                    draft.document.save(cmd_args.output)

                print(json.dumps(draft.to_dict(), indent=2))

            elif subcommand == "analyze":
                cmd_parser.add_argument("path", type=str)
                cmd_args = cmd_parser.parse_args(args.subcommand_args[1:] + unknown)

                result = wb.analyze(cmd_args.path)
                if hasattr(result, "to_dict"):
                    result = result.to_dict()
                print(json.dumps(result, indent=2))

            elif subcommand == "review":
                cmd_parser.add_argument("path", type=str)
                cmd_args = cmd_parser.parse_args(args.subcommand_args[1:] + unknown)

                wb.open(cmd_args.path)
                from .analysis.draft import SpriteDraft
                draft = SpriteDraft(wb.document)
                result = wb.review(draft)
                print(json.dumps(result, indent=2))

            elif subcommand == "repair":
                cmd_parser.add_argument("path", type=str)
                cmd_parser.add_argument("--output", type=str)
                cmd_parser.add_argument("--dry-run", action="store_true")
                cmd_args = cmd_parser.parse_args(args.subcommand_args[1:] + unknown)

                wb.open(cmd_args.path)
                result = wb.repair(dry_run=cmd_args.dry_run)
                if cmd_args.output and not cmd_args.dry_run:
                    wb.save(cmd_args.output)
                print(json.dumps(result, indent=2))

            elif subcommand == "regression":
                cmd_parser.add_argument("before", type=str)
                cmd_parser.add_argument("after", type=str)
                cmd_args = cmd_parser.parse_args(args.subcommand_args[1:] + unknown)

                result = wb.regression_report(cmd_args.before, cmd_args.after)
                print(json.dumps(result, indent=2))

            elif subcommand == "grid":
                cmd_parser.add_argument("path", type=str)
                cmd_args = cmd_parser.parse_args(args.subcommand_args[1:] + unknown)

                wb.open(cmd_args.path)
                print(json.dumps(wb.to_ascii_grid(include_legend=True), indent=2))

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
