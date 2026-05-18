"""Entry point for `python -m elixis` and `elixis` CLI command."""

import os
import sys

HELP_TEXT = """usage: elixis [--port PORT]

Start the Elixis HTTP server.

options:
  -h, --help   show this help message and exit
  --port PORT  port to bind (default: 3110)
"""


# Ensure the parent directory is on the path so `app.py` can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _validate_args(args):
    """Fail fast on unsupported CLI arguments before starting the server."""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--port":
            if i + 1 >= len(args):
                sys.stderr.write("error: --port requires a value\n")
                return 2
            try:
                int(args[i + 1])
            except ValueError:
                sys.stderr.write(f"error: invalid --port value: {args[i + 1]}\n")
                return 2
            i += 2
            continue
        sys.stderr.write(f"error: unknown argument: {arg}\n")
        return 2
    return 0


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    if any(arg in {"-h", "--help"} for arg in args):
        print(HELP_TEXT)
        return 0
    validation_status = _validate_args(args)
    if validation_status:
        sys.stderr.write(HELP_TEXT)
        return validation_status

    from app import main as app_main

    return app_main()


if __name__ == "__main__":
    sys.exit(main())
