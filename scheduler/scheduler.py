"""
Cooperative scheduler module for MicroPython.

Usage:
    from scheduler import Task, run

    tasks = [
        Task(my_func, interval_ms=500),
        Task(another_func, interval_ms=100),
    ]
    scheduler = run(tasks)                    # tight loop (default)
    scheduler = run(tasks, light_sleep=True)  # sleep between rounds to save power

    while True:
        next(scheduler)  # advance one round; add per-round logic here if needed
"""

from utime import ticks_diff, ticks_ms  # type: ignore

MIN_SLEEP_MS = 1  # don't sleep for less than this; avoids overhead on very short gaps


class Task:
    def __init__(self, task_to_run, interval_ms, last_ms=0):
        self.task_to_run = task_to_run
        self.interval_ms = interval_ms
        self.last_ms = last_ms


def run(tasks, light_sleep=False, min_sleep_ms=MIN_SLEEP_MS):
    """
    Generator-based scheduler. Yields after each round so the caller controls
    the loop via next().

    tasks        -- list of Task objects
    light_sleep  -- if True, sleep between rounds using machine.lightsleep()
                    to reduce power consumption (default: False)
    min_sleep_ms -- minimum gap worth sleeping; shorter gaps use a tight loop
                    (default: MIN_SLEEP_MS)
    """
    if light_sleep:
        import machine  # type: ignore  # imported lazily; only needed when sleep is enabled

        # The shortest interval is the scheduler tick rate — sleep no longer than this.
        sleep_for = max(min_sleep_ms, min(task.interval_ms for task in tasks))

    while True:
        now = ticks_ms()

        for task in tasks:
            if ticks_diff(now, task.last_ms) >= task.interval_ms:
                task.last_ms = now
                task.task_to_run()

        if light_sleep:
            machine.lightsleep(sleep_for)

        yield
