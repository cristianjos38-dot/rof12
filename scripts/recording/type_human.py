#!/usr/bin/env python3
"""Type a safe, non-secret demo command with human-like timing on macOS.

Dry-run is the default. Pass ``--send`` only when the intended terminal or
browser field is visibly focused. This utility never reads or prints secrets.
"""
from __future__ import annotations

import argparse
import random
import subprocess
import time


def type_human(text: str, *, send: bool = False, seed: int | None = None) -> None:
    if not text or len(text) > 500:
        raise ValueError("demo text must contain 1..500 characters")
    rng = random.Random(seed)
    if not send:
        print(f"[DRY RUN] {text}")
        return
    for character in text:
        script = f'tell application "System Events" to keystroke {character!r}'
        subprocess.run(["osascript", "-e", script], check=True)
        time.sleep(rng.uniform(0.05, 0.10))


def main() -> int:
    parser = argparse.ArgumentParser(description="ROF12 human-paced demo typing")
    parser.add_argument("text", help="synthetic demo text; never pass credentials")
    parser.add_argument("--send", action="store_true", help="send keystrokes to the focused app")
    parser.add_argument("--seed", type=int, default=None, help="repeatable timing seed for rehearsal")
    args = parser.parse_args()
    type_human(args.text, send=args.send, seed=args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
