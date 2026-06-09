from __future__ import annotations

import subprocess
import sys

from .servers import FACTORIES, run


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m idp_mcp <documents|relational|vector|graph|all>")
    name = sys.argv[1]
    if name == "all":
        procs = [subprocess.Popen([sys.executable, "-m", "idp_mcp", n]) for n in FACTORIES]
        for p in procs:
            p.wait()
    else:
        run(name)


if __name__ == "__main__":
    main()
