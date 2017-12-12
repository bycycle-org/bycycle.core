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

    def __init__(self):
        self.started = False
        self.start_time = None
        self.stopped = False
        self.total_time = None

    @property
    def elapsed_time(self):
        if self.stopped:
            return self.total_time
        else:
            return time.time() - self.start_time

    def start(self):
        if self.started:
            raise TimerError('Already started')
        self.started = True
        self.start_time = time.time()
        self.stopped = False
        self.total_time = None

    def stop(self):
        if not self.started:
            raise TimerError('Not started')
        if self.stopped:
            raise TimerError('Already stopped')
        self.started = False
        self.stopped = True
        self.total_time = time.time() - self.start_time

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_traceback):
        self.stop()

    def __str__(self):
        m, s = divmod(self.elapsed_time, 60)
        if m:
            s = int(round(s))
            return '{m}m {s}s'.format(m=int(m), s=s)
        else:
            return '{s:.2f}s'.format(s=s)


class PeriodicRunner(Thread):

    """Runs a function periodically until stopped.

    Like a normal thread, call :meth:`start` to start running the
    function. Call :meth:`stop` to stop it. The default sleep time is
    1 second. Pass an ``interval`` as an int or float to changee this.

    """

    def __init__(self, target, args=(), kwargs=None, interval=1):
        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs if kwargs is not None else {}
        self.interval = interval
        self.stopped = Event()

    def run(self):
        self.target(*self.args, **self.kwargs)
        while not self.stopped.wait(self.interval):
            self.target(*self.args, **self.kwargs)

    def stop(self):
        self.stopped.set()
