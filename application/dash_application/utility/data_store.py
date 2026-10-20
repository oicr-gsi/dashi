import threading

_lock = threading.Lock()


class DataStore:
    def __init__(self):
        self._data = None

    def get(self):
        with _lock:
            return self._data

    def set(self, data):
        with _lock:
            self._data = data


def set_all(updates):
    with _lock:
        for store, data in updates:
            store._data = data
