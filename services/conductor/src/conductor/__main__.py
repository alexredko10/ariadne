"""
``python -m conductor`` entry point. Delegates to subcommand parsers.
"""

from __future__ import annotations

import sys

from .dry_run import main as dry_run_main
from .demo_flow import main as demo_main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dry-run":
        raise SystemExit(dry_run_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "ariadne-demo":
        raise SystemExit(demo_main(sys.argv[2:]))
    print("usage: python -m conductor dry-run | ariadne-demo", file=sys.stderr)
    raise SystemExit(2)
