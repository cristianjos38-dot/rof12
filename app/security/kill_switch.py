from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import text


@dataclass(frozen=True)
class SystemState:
    active: bool
    reason: str = ""
    updated_at: datetime | None = None


class KillSwitchError(ValueError):
    pass


class KillSwitch:
    AUTHORIZED_ROLES = frozenset({"admin", "security_admin"})

    def read(self, connection) -> SystemState:
        row = connection.execute(text("SELECT kill_switch_active, reason, updated_at FROM rof12.system_state WHERE state_id = true FOR SHARE")).mappings().first()
        if not row:
            return SystemState(False)
        return SystemState(bool(row["kill_switch_active"]), row.get("reason", ""), row.get("updated_at"))

    def activate(self, connection, ctx, reason: str) -> SystemState:
        if getattr(ctx, "role", None) not in self.AUTHORIZED_ROLES:
            raise KillSwitchError("role cannot activate kill switch")
        now = datetime.now(UTC)
        result = connection.execute(text("UPDATE rof12.system_state SET kill_switch_active = true, reason = :reason, updated_at = :now WHERE state_id = true"), {"reason": reason, "now": now})
        if result.rowcount != 1:
            raise KillSwitchError("system state could not be updated")
        connection.execute(text("UPDATE rof12.capabilities SET status = 'REVOKED' WHERE status = 'ACTIVE'"))
        return SystemState(True, reason, now)

    def deactivate(self, connection, ctx) -> SystemState:
        if getattr(ctx, "role", None) not in self.AUTHORIZED_ROLES:
            raise KillSwitchError("role cannot deactivate kill switch")
        now = datetime.now(UTC)
        result = connection.execute(text("UPDATE rof12.system_state SET kill_switch_active = false, reason = '', updated_at = :now WHERE state_id = true"), {"now": now})
        if result.rowcount != 1:
            raise KillSwitchError("system state could not be updated")
        return SystemState(False, "", now)

    def reject_if_active(self, connection):
        if self.read(connection).active:
            raise KillSwitchError("KILL_SWITCH_ACTIVE")

