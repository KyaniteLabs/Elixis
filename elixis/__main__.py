"""Command-line interface for Elixis."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from . import __version__


# Ensure the parent directory is on the path so `app.py` can be found when the
# package is run directly from a checkout.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="elixis",
        description="Elixis local-first pattern synthesis operator CLI.",
    )
    parser.add_argument("--version", action="store_true", help="show version and exit")
    parser.add_argument("--port", type=int, default=None, help="serve HTTP API on port (default: 3110)")

    subparsers = parser.add_subparsers(dest="command")

    serve = subparsers.add_parser("serve", help="start the HTTP API server")
    serve.add_argument("--port", type=int, default=3110, help="port to bind (default: 3110)")

    run = subparsers.add_parser("run", help="run synthesis through an output lens")
    _add_text_input_args(run)
    run.add_argument("--lens", choices=("identity", "brand", "design"), default="identity")
    run.add_argument("--json", action="store_true", help="emit JSON summary instead of markdown output")

    extract = subparsers.add_parser("extract", help="extract structured entities from text")
    _add_text_input_args(extract)
    extract.add_argument("--json", action="store_true", default=True, help=argparse.SUPPRESS)

    patterns = subparsers.add_parser("patterns", help="analyze archetypal patterns in text")
    _add_text_input_args(patterns)

    name = subparsers.add_parser("name", help="research names or generate names from synthesized identity")
    name_input = name.add_mutually_exclusive_group(required=True)
    name_input.add_argument("--name", help="name or concept to research")
    name_input.add_argument("--text", help="raw identity/reference text to synthesize before naming")
    name_input.add_argument("--file", help="file containing raw identity/reference text")
    name.add_argument("--context", default="", help="naming context, such as product category or audience")
    name.add_argument("--source", choices=("general", "taxonomy"), default="taxonomy")
    name.add_argument("--no-variants", action="store_true", help="skip variant generation for --name")

    subparsers.add_parser("mcp", help="run the MCP stdio server")
    return parser


def _add_text_input_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="raw reference text")
    group.add_argument("--file", help="file containing raw reference text")
    group.add_argument("--stdin", action="store_true", help="read raw reference text from stdin")


def _read_text(args: argparse.Namespace) -> str:
    if getattr(args, "text", None) is not None:
        return args.text
    if getattr(args, "file", None):
        with open(args.file, encoding="utf-8") as f:
            return f.read()
    if getattr(args, "stdin", False):
        return sys.stdin.read()
    raise ValueError("expected --text, --file, or --stdin")


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _run_server(port: int) -> Any:
    from app import main as app_main

    old_argv = sys.argv[:]
    try:
        sys.argv = [old_argv[0], "--port", str(port)]
        return app_main()
    finally:
        sys.argv = old_argv


def _cmd_run(args: argparse.Namespace) -> int:
    from .engine import GameEngine
    from .process_trace import process_trace_from_state
    from .validation import validate_brain_dump

    text = _read_text(args)
    is_valid, error, meta = validate_brain_dump(text)
    if not is_valid:
        sys.stderr.write(f"error: {error}\n")
        return 2

    engine = GameEngine()
    output = engine.run_full(meta.get("sanitized_text", text), lens=args.lens)
    if args.json:
        state = engine.state
        graph = state.metadata.get("pattern_graph", {})
        _print_json({
            "lens": args.lens,
            "entity_count": len(state.beads),
            "thread_count": len(state.threads),
            "tension_count": len(state.tensions),
            "top_patterns": [p.get("name") for p in graph.get("patterns", [])[:3]],
            "emergent_topic": graph.get("emergent_topic"),
            "emergent_theme": graph.get("emergent_theme"),
            "consensus_score": graph.get("consensus_score"),
            "process_trace": process_trace_from_state(state, lens=args.lens),
            "output": output,
        })
    else:
        print(output)
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    from .entities import extract_entities
    from .validation import validate_brain_dump

    text = _read_text(args)
    is_valid, error, meta = validate_brain_dump(text)
    if not is_valid:
        sys.stderr.write(f"error: {error}\n")
        return 2
    _print_json(extract_entities(meta.get("sanitized_text", text)))
    return 0


def _cmd_patterns(args: argparse.Namespace) -> int:
    from .entities import extract_entities
    from .patterns import build_pattern_graph
    from .validation import validate_brain_dump

    text = _read_text(args)
    is_valid, error, meta = validate_brain_dump(text)
    if not is_valid:
        sys.stderr.write(f"error: {error}\n")
        return 2
    text = meta.get("sanitized_text", text)
    entities = extract_entities(text)
    _print_json(build_pattern_graph(entities, text))
    return 0


def _cmd_name(args: argparse.Namespace) -> int:
    if args.name:
        from .naming import research_name

        _print_json(research_name(
            args.name,
            args.context,
            generate_variants=not args.no_variants,
            source=args.source,
        ))
        return 0

    from .engine import GameEngine
    from .validation import validate_brain_dump

    text = args.text if args.text is not None else open(args.file, encoding="utf-8").read()
    is_valid, error, meta = validate_brain_dump(text)
    if not is_valid:
        sys.stderr.write(f"error: {error}\n")
        return 2

    engine = GameEngine()
    engine.declare_themes(meta.get("sanitized_text", text))
    engine.elaborate()
    engine.connect_domains()
    _print_json(engine.name(source=args.source))
    return 0


def _cmd_mcp(_args: argparse.Namespace) -> int:
    from .mcp_server import main as mcp_main

    mcp_main()
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    if args.version:
        print(f"elixis {__version__}")
        return 0

    if args.command in (None, "serve"):
        return _run_server(args.port or 3110)
    if args.command == "run":
        return _cmd_run(args)
    if args.command == "extract":
        return _cmd_extract(args)
    if args.command == "patterns":
        return _cmd_patterns(args)
    if args.command == "name":
        return _cmd_name(args)
    if args.command == "mcp":
        return _cmd_mcp(args)

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
