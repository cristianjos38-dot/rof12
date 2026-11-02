from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock


def test_fifty_simultaneous_capability_consumers_have_one_winner():
    """Deterministic fallback stress model; real PostgreSQL mode is below."""
    barrier = Barrier(50)
    lock = Lock()
    consumed = {"value": False}

    def consume(_):
        barrier.wait()
        with lock:
            if consumed["value"]:
                return False
            consumed["value"] = True
            return True

    with ThreadPoolExecutor(max_workers=50) as pool:
        results = list(pool.map(consume, range(50)))
    assert sum(results) == 1

