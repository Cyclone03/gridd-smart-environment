import threading
from concurrent.futures import Future


class ReplyRegistry:
    """Réponses attendues par les commandes en cours, par ``correlation_id``."""

    def __init__(self):
        self._pending = {}
        self._lock = threading.Lock()

    def expect(self, correlation_id) -> Future:
        future = Future()
        with self._lock:
            self._pending[correlation_id] = future
        return future

    def resolve(self, event) -> bool:
        with self._lock:
            future = self._pending.pop(event.correlation_id, None)
        if future is None or future.done():
            return False
        future.set_result(event)
        return True

    def discard(self, correlation_id):
        with self._lock:
            self._pending.pop(correlation_id, None)
