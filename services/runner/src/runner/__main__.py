"""
``python -m runner`` entry point. Delegates to subcommand parsers.
"""

from __future__ import annotations

import sys

from .doctor import main as doctor_main
from .runtime_smoke import main as smoke_main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "runtime-smoke":
        raise SystemExit(smoke_main(sys.argv[2:]))
    raise SystemExit(doctor_main())
