#!/usr/bin/env python3
"""Simple repeatable terminal demo entry point."""
import argparse, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--interactive", action="store_true", help="pause between attacks")
args = parser.parse_args()
sys.path.insert(0, str(ROOT / "src"))
import json
from rof12.core import ROF12Round
engine = ROF12Round(ROOT / "policy/policy.json")
for path in sorted((ROOT / "attacks").glob("ATK-*.json")):
    attack = json.loads(path.read_text())
    result = engine.run(attack)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.interactive:
        input("Presiona Enter para continuar...")
print("AUDIT_CHAIN_VALID=", engine.audit.verify())
