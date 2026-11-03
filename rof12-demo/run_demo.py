#!/usr/bin/env python3
"""ROF12 — demos de seguridad para agentes.

  python run_demo.py            # las 3 demos
  python run_demo.py 1          # solo DEMO 01 (también: 2, 3, all)
  python run_demo.py all --step # pausa entre pasos (ideal para grabar / presentar)
  python run_demo.py all --fast # sin retardos
  python run_demo.py 3 --interactive   # tú apruebas o rechazas el hold
  python run_demo.py audit [--tamper-test]
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rof12.ui import UI
from rof12.demos import Ctx, HERE, audit_cmd, demo1, demo2, demo3


def main():
    ap = argparse.ArgumentParser(description="ROF12 demos")
    ap.add_argument("which", nargs="?", default="all", choices=["1", "2", "3", "all", "audit"])
    ap.add_argument("--step", action="store_true", help="pausar entre pasos (Enter)")
    ap.add_argument("--fast", action="store_true", help="sin retardos")
    ap.add_argument("--delay", type=float, default=0.12, help="retardo por línea (s)")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--force-color", action="store_true", help="colores aunque no sea TTY")
    ap.add_argument("--interactive", action="store_true", help="aprobar/rechazar el hold a mano en la demo 3")
    ap.add_argument("--tamper-test", action="store_true", help="con 'audit': demuestra detección de manipulación")
    ap.add_argument("--audit-path", default=os.path.join(HERE, "out", "audit.jsonl"))
    a = ap.parse_args()

    color = False if a.no_color else ("force" if a.force_color else True)
    ui = UI(color=color, delay=0 if a.fast else a.delay, step=a.step)

    if a.which == "audit":
        sys.exit(audit_cmd(ui, a.audit_path, a.tamper_test))

    ctx = Ctx(ui, a.audit_path, interactive=a.interactive)
    todo = {"1": [demo1], "2": [demo2], "3": [demo3], "all": [demo1, demo2, demo3]}[a.which]
    for fn in todo:
        fn(ctx)
    ui.out()
    ui.out(ui.c(f"Audit log: {a.audit_path}   (verifica con: python run_demo.py audit --tamper-test)", "gray"))


if __name__ == "__main__":
    main()
