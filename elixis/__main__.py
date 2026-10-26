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

    ingest = subparsers.add_parser("ingest", help="build a Source Corpus and optional Market Kit")
    ingest_target = ingest.add_mutually_exclusive_group(required=True)
    ingest_target.add_argument("--github", help="GitHub repository URL to ingest")
    ingest_target.add_argument("--path", help="local folder path to ingest")
    ingest.add_argument("--kit", action="store_true", help="include Market Kit orchestration")
    ingest.add_argument("--json", action="store_true", default=True, help=argparse.SUPPRESS)
    ingest.add_argument("--artifact", action="append", default=[], help="render artifact tier: markdown, html, css, or market-page")
    ingest.add_argument("--include-code", action="store_true", help="include supporting code evidence")
    ingest.add_argument("--include-issues", action="store_true", help="include GitHub issue evidence")
    ingest.add_argument("--include-prs", action="store_true", help="include GitHub pull request evidence")
    ingest.add_argument("--include-commits", action="store_true", help="include GitHub commit trajectory evidence")
    ingest.add_argument("--include-hidden", action="store_true", help="include hidden local files when safe")
    ingest.add_argument("--include-large-files", action="store_true", help="allow large text files into scoring")
    ingest.add_argument("--include-visual-analysis", action="store_true", help="mark visual assets for downstream visual analysis")
    ingest.add_argument("--max-signals", type=int, default=80, help="maximum Corpus Signals to include")

    corpus = subparsers.add_parser("corpus", help="inspect persisted Source Corpus runs")
    corpus_sub = corpus.add_subparsers(dest="corpus_command", required=True)
    corpus_inspect = corpus_sub.add_parser("inspect", help="inspect an Ingestion Result by run ID")
    corpus_inspect.add_argument("run_id")

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


def _prepared(text: str) -> str | None:
    """Validated text, or None after reporting the error on stderr."""
    from .service import InvalidInput, prepare_text

    try:
        return prepare_text(text)
    except InvalidInput as error:
        sys.stderr.write(f"error: {error}\n")
        return None


def _cmd_run(args: argparse.Namespace) -> int:
    from .service import synthesize

    text = _prepared(_read_text(args))
    if text is None:
        return 2
    run = synthesize(text, lens=args.lens)
    if args.json:
        _print_json(run.summary())
    else:
        print(run.output)
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    from .entities import extract_entities

    text = _prepared(_read_text(args))
    if text is None:
        return 2
    _print_json(extract_entities(text))
    return 0


def _cmd_patterns(args: argparse.Namespace) -> int:
    from .service import patterns

    text = _prepared(_read_text(args))
    if text is None:
        return 2
    _print_json(patterns(text))
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

    from .service import name_from_identity

    text = _prepared(args.text if args.text is not None else open(args.file, encoding="utf-8").read())
    if text is None:
        return 2
    _print_json(name_from_identity(text, source=args.source))
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    if args.kit:
        from .market import create_market_kit

        result = create_market_kit(
            github=args.github,
            path=args.path,
            artifacts=args.artifact,
            include_code=args.include_code,
            include_issues=args.include_issues,
            include_prs=args.include_prs,
            include_commits=args.include_commits,
            include_hidden=args.include_hidden,
            include_large_files=args.include_large_files,
            include_visual_analysis=args.include_visual_analysis,
            max_signals=args.max_signals,
        )
    else:
        from .ingest import ingest_source

        result = ingest_source(
            github=args.github,
            path=args.path,
            artifacts=args.artifact,
            include_code=args.include_code,
            include_issues=args.include_issues,
            include_prs=args.include_prs,
            include_commits=args.include_commits,
            include_hidden=args.include_hidden,
            include_large_files=args.include_large_files,
            include_visual_analysis=args.include_visual_analysis,
            max_signals=args.max_signals,
        )
    _print_json(result)
    return 0


def _cmd_corpus(args: argparse.Namespace) -> int:
    from .ingest import load_ingestion_result

    if args.corpus_command == "inspect":
        _print_json(load_ingestion_result(args.run_id))
        return 0
    raise AssertionError(f"unhandled corpus command: {args.corpus_command}")


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
    if args.command == "ingest":
        return _cmd_ingest(args)
    if args.command == "corpus":
        return _cmd_corpus(args)
    if args.command == "mcp":
        return _cmd_mcp(args)

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
