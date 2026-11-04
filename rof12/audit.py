"""Registro de auditoria append-only con cadena de hashes (tamper-evident)."""
from __future__ import annotations

import hashlib, json, os, time

GENESIS = "0" * 64


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _hash(prev: str, body: dict) -> str:
    return hashlib.sha256((prev + canon(body)).encode("utf-8")).hexdigest()


class Audit:
    def __init__(self, path: str, reset: bool = True):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if reset and os.path.exists(path):
            os.remove(path)
        self._seq, self._prev = 0, GENESIS
        if os.path.exists(path):
            recs = self.records()
            if recs:
                self._seq, self._prev = recs[-1]["seq"], recs[-1]["hash"]

    def append(self, event: str, summary: str, **data) -> dict:
        self._seq += 1
        body = {"seq": self._seq, "ts": round(time.time(), 3), "event": event,
                "summary": summary, "data": data, "prev": self._prev}
        body["hash"] = _hash(self._prev, body)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(canon(body) + "\n")
        self._prev = body["hash"]
        return body

    def records(self) -> list:
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    @staticmethod
    def verify(path: str):
        """Devuelve (ok, n_registros, seq_roto | None, hash_cabeza)."""
        prev, n = GENESIS, 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                n += 1
                claimed = rec.pop("hash")
                if rec.get("prev") != prev or _hash(prev, rec) != claimed:
                    return False, n, rec.get("seq"), prev
                prev = claimed
        return True, n, None, prev
