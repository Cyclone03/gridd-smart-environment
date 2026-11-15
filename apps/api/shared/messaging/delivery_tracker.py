import threading


class DeliveryTracker:
    """Suivi des accusés de réception d'un ensemble de messages publiés.

    Le rappel de livraison peut être exécuté par n'importe quel thread qui
    sert le producteur partagé (``poll`` / ``flush``) : compteurs protégés.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._sent = 0
        self._delivered = 0
        self._errors = []

    def sent(self):
        with self._lock:
            self._sent += 1

    def on_delivery(self, error, _message):
        with self._lock:
            if error is None:
                self._delivered += 1
            else:
                self._errors.append(error)

    @property
    def outstanding(self) -> int:
        with self._lock:
            return self._sent - self._delivered - len(self._errors)

    @property
    def first_error(self):
        with self._lock:
            return self._errors[0] if self._errors else None
