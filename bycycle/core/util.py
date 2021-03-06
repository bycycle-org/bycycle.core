import time
from threading import Event, Thread


class TimerError(Exception):

    pass


class Timer:

    """A super simple wall clock timer.

    After an instance is created, it must be started with
    :meth:`start`. It will run until it is :meth:`stop`pped.

    A timer can be reset/reused by calling :meth:`stop` then
    :meth:`start`.

    The string value of a timer is its current elapsed time.

    Can be used as a context manager, in which case the timer will be
    started and stopped automatically::

        with Timer() as t:  # t is automatically start()ed
            do_something()
        # t is automatically stop()ped
        print(t)

    """

    def __init__(self, autoprint=False):
        self.started = False
        self.start_time = None
        self.stopped = False
        self.total_time = None
        self.autoprint = autoprint

    @property
    def elapsed_time(self):
        if self.stopped:
            return self.total_time
        else:
            return time.monotonic() - self.start_time

    def start(self):
        if self.started:
            raise TimerError('Already started')
        self.started = True
        self.start_time = time.monotonic()
        self.stopped = False
        self.total_time = None

    def stop(self):
        if not self.started:
            raise TimerError('Not started')
        if self.stopped:
            raise TimerError('Already stopped')
        self.started = False
        self.stopped = True
        self.total_time = time.monotonic() - self.start_time
        if self.autoprint:
            print(self)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_traceback):
        self.stop()

    def __str__(self):
        m, s = divmod(self.elapsed_time, 60)
        if m:
            return '{m}m {s:.1f}s'.format(m=int(m), s=s)
        if s > 0.01:
            return '{s:.2f}s'.format(s=s)
        if s > 0.001:
            ms = s * 1_000
            return '{ms:.0f}ms'.format(ms=ms)
        if s > 0.000001:
            us = s * 1_000_000
            return '{us:.0f}us'.format(us=us)
        ns = s * 1_000_000_000
        return '{ns:.0f}ns'.format(ns=ns)


class PeriodicRunner(Thread):

    """Run a function periodically until stopped.

    Like a normal thread, call :meth:`start` to start running the
    function. Call :meth:`stop` to stop it. The default sleep time is 1
    second. Pass an ``interval`` as an int or float to changee this.

    """

    def __init__(self, target, interval=1, **kwargs):
        super().__init__(target=target, daemon=True, **kwargs)
        self._interval = interval
        self._stopped = Event()

    def run(self):
        while True:
            self._target(*self._args, **self._kwargs)
            if self._stopped.wait(self._interval):
                break

    def stop(self):
        self._stopped.set()
