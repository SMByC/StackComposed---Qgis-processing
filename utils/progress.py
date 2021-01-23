import threading
import time
from timeit import default_timer

from dask.callbacks import Callback


class ProgressBar(Callback):
    def __init__(self, minimum=0, dt=0.1, feedback=None):
        self._minimum = minimum
        self._dt = dt
        self._feedback = feedback
        self.last_duration = 0

    def _start(self, dsk):
        self._state = None
        self._start_time = default_timer()
        # Start background thread
        self._running = True
        self._timer = threading.Thread(target=self._timer_func)
        self._timer.daemon = True
        self._timer.start()

    def _pretask(self, key, dsk, state):
        self._state = state

    def _finish(self, dsk, state, errored):
        self._running = False
        self._timer.join()
        elapsed = default_timer() - self._start_time
        self.last_duration = elapsed
        if elapsed < self._minimum:
            return
        if not errored:
            self._draw_bar(1)
        else:
            self._update_bar()

    def _timer_func(self):
        """Background thread for updating the progress bar"""
        while self._running:
            elapsed = default_timer() - self._start_time
            if elapsed > self._minimum:
                self._update_bar()
            time.sleep(self._dt)

    def _update_bar(self):
        s = self._state
        if not s:
            self._draw_bar(0)
            return
        ndone = len(s["finished"])
        ntasks = sum(len(s[k]) for k in ["ready", "waiting", "running"]) + ndone
        if ndone < ntasks:
            self._draw_bar(ndone / ntasks if ntasks else 0)

    def _draw_bar(self, frac):
        percent = int(100 * frac)
        if not self._feedback.isCanceled():
            self._feedback.setProgress(percent)