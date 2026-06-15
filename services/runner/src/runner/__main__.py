"""
``python -m runner`` entry point. Delegates to subcommand parsers.
"""

from __future__ import annotations

from .doctor import main

if __name__ == "__main__":
    raise SystemExit(main())
