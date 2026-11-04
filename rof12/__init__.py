"""Optional top-level adapters for the ROF12 runtime.

The standalone terminal keeps the historical demo modules in
``rof12-demo/rof12``.  Extending the package path lets the runner import those
modules without duplicating or replacing the security implementation.
"""
from pathlib import Path

_demo_package = Path(__file__).resolve().parents[1] / "rof12-demo" / "rof12"
if _demo_package.is_dir() and str(_demo_package) not in __path__:
    __path__.append(str(_demo_package))
