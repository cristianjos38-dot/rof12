"""CLI name kept stable for the three-minute release demonstration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.replay import main

if __name__ == "__main__":
    main()
