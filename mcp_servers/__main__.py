"""Lanceur des serveurs MCP.

    python -m mcp_servers documents   # un seul (bloquant)
    python -m mcp_servers all         # les quatre (sous-process)
"""
from __future__ import annotations

import subprocess
import sys
import time

from .servers import FACTORIES, PORTS, run


def _all() -> None:
    procs = []
    for name in FACTORIES:
        procs.append(subprocess.Popen([sys.executable, "-m", "mcp_servers", name]))
        print(f"▶ {name} → http://127.0.0.1:{PORTS[name]}/mcp")
    print("Ctrl-C pour tout arrêter.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    _all() if arg == "all" else run(arg)
