"""Entry point for `python -m elixis` and `elixis` CLI command."""

import sys
import os

# Ensure the parent directory is on the path so `app.py` can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from app import main as app_main
    app_main()


if __name__ == "__main__":
    main()
