from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.observability import decision_counts

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    lines = ["# TYPE rof12_gate_decisions_total counter"]
    for decision, count in sorted(decision_counts.items()):
        lines.append(f'rof12_gate_decisions_total{{decision="{decision}"}} {count}')
    return "\n".join(lines) + "\n"
