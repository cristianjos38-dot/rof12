from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "adversarial"


@dataclass(frozen=True)
class DemoFixture:
    fixture_id: str
    path: Path
    sha256: str


def load_fixtures() -> tuple[DemoFixture, ...]:
    paths = tuple(sorted(FIXTURE_ROOT.iterdir()))
    if len(paths) != 7:
        raise RuntimeError(f"expected exactly seven adversarial fixtures, found {len(paths)}")
    return tuple(
        DemoFixture(path.stem, path, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in paths
    )
