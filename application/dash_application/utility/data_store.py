import threading


class DataStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = None

    def get(self):
        with self._lock:
            return self._data

    def set(self, data):
        with self._lock:
            self._data = data

