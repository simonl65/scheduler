import importlib
import sys
import types

import pytest

TICKS_PERIOD = 2**30


class FakeUtime:
    """Minimal ticks_ms()/ticks_diff() double with real wraparound math,
    matching MicroPython's rp2 ticks period. `now` is set directly by
    tests rather than advancing with wall-clock time."""

    def __init__(self):
        self.now = 0

    def ticks_ms(self):
        return self.now

    def ticks_diff(self, a, b):
        diff = (a - b) & (TICKS_PERIOD - 1)
        if diff >= TICKS_PERIOD // 2:
            diff -= TICKS_PERIOD
        return diff


@pytest.fixture
def fake_utime(monkeypatch):
    fake = FakeUtime()
    monkeypatch.setitem(sys.modules, "utime", fake)
    return fake


@pytest.fixture
def scheduler_module(fake_utime, monkeypatch):
    # `pythonpath = ["scheduler"]` (see pyproject.toml) puts the package
    # directory itself on sys.path, so `import scheduler` resolves directly
    # to scheduler/scheduler.py rather than the package's __init__.py.
    monkeypatch.delitem(sys.modules, "machine", raising=False)
    monkeypatch.delitem(sys.modules, "scheduler", raising=False)
    import scheduler as module

    return importlib.reload(module)


def test_task_does_not_fire_before_due(scheduler_module, fake_utime):
    calls = []
    fake_utime.now = 0
    task = scheduler_module.Task(lambda: calls.append("a"), interval_ms=10)
    fake_utime.now = 9

    next(scheduler_module.run([task]))

    assert calls == []


def test_task_fires_when_due(scheduler_module, fake_utime):
    calls = []
    fake_utime.now = 0
    task = scheduler_module.Task(lambda: calls.append("a"), interval_ms=10)
    fake_utime.now = 10

    next(scheduler_module.run([task]))

    assert calls == ["a"]


def test_tasks_run_in_declared_list_order(scheduler_module, fake_utime):
    calls = []
    fake_utime.now = 0
    tasks = [
        scheduler_module.Task(lambda i=i: calls.append(i), interval_ms=0)
        for i in range(3)
    ]

    next(scheduler_module.run(tasks))

    assert calls == [0, 1, 2]


def test_interval_zero_runs_every_round(scheduler_module, fake_utime):
    calls = []
    fake_utime.now = 0
    task = scheduler_module.Task(lambda: calls.append("a"), interval_ms=0)
    scheduler = scheduler_module.run([task])

    next(scheduler)
    fake_utime.now = 1
    next(scheduler)
    fake_utime.now = 1  # same tick again -- still due at interval_ms=0
    next(scheduler)

    assert calls == ["a", "a", "a"]


def test_tick_wraparound_is_handled_via_ticks_diff(
    scheduler_module, fake_utime
):
    calls = []
    fake_utime.now = TICKS_PERIOD - 5
    task = scheduler_module.Task(lambda: calls.append("a"), interval_ms=10)
    # advance past the wraparound boundary by 12ms of real elapsed time
    fake_utime.now = (TICKS_PERIOD - 5 + 12) % TICKS_PERIOD

    next(scheduler_module.run([task]))

    assert calls == ["a"]


def test_overrun_coalesces_without_catch_up(scheduler_module, fake_utime):
    calls = []
    fake_utime.now = 0
    task = scheduler_module.Task(lambda: calls.append("a"), interval_ms=10)
    fake_utime.now = 100  # ten intervals overdue

    next(scheduler_module.run([task]))

    assert calls == ["a"]  # fires once, not ten times
    assert task.last_ms == 100  # set to `now`, not last_ms + interval_ms


def test_last_ms_defaults_to_ticks_ms_at_construction(
    scheduler_module, fake_utime
):
    fake_utime.now = 42

    task = scheduler_module.Task(lambda: None, interval_ms=10)

    assert task.last_ms == 42  # not 0 -- a task built after uptime has
    # advanced must not be treated as overdue since boot


def test_last_ms_can_be_explicitly_set(scheduler_module, fake_utime):
    fake_utime.now = 42

    task = scheduler_module.Task(lambda: None, interval_ms=10, last_ms=7)

    assert task.last_ms == 7


def test_isolated_task_exception_does_not_propagate(
    scheduler_module, fake_utime
):
    fake_utime.now = 0

    def failing():
        raise ValueError("sensor fault")

    task = scheduler_module.Task(failing, interval_ms=0)

    next(scheduler_module.run([task]))  # must not raise

    assert isinstance(task.last_exception, ValueError)


def test_isolation_does_not_block_later_tasks_in_the_same_round(
    scheduler_module, fake_utime
):
    calls = []
    fake_utime.now = 0

    def failing():
        raise ValueError("sensor fault")

    failing_task = scheduler_module.Task(failing, interval_ms=0)
    later_task = scheduler_module.Task(
        lambda: calls.append("later"), interval_ms=0
    )

    next(scheduler_module.run([failing_task, later_task]))

    assert calls == ["later"]


def test_exempt_task_exception_propagates(scheduler_module, fake_utime):
    fake_utime.now = 0

    def failing():
        raise ValueError("watchdog fault")

    task = scheduler_module.Task(failing, interval_ms=0, isolate_errors=False)
    scheduler = scheduler_module.run([task])

    with pytest.raises(ValueError):
        next(scheduler)


def test_light_sleep_defaults_off_and_never_imports_machine(
    scheduler_module, fake_utime
):
    fake_utime.now = 0
    task = scheduler_module.Task(lambda: None, interval_ms=0)

    next(scheduler_module.run([task]))  # must not raise ImportError

    assert "machine" not in sys.modules


def test_light_sleep_enabled_lazily_imports_and_calls_lightsleep(
    scheduler_module, fake_utime, monkeypatch
):
    sleep_calls = []
    fake_machine = types.SimpleNamespace(
        lightsleep=lambda ms: sleep_calls.append(ms)
    )
    monkeypatch.setitem(sys.modules, "machine", fake_machine)
    fake_utime.now = 0
    task = scheduler_module.Task(lambda: None, interval_ms=50)

    next(scheduler_module.run([task], light_sleep=True))

    assert sleep_calls == [50]


def test_run_is_a_generator_one_round_per_next_call(
    scheduler_module, fake_utime
):
    calls = []
    fake_utime.now = 0
    task = scheduler_module.Task(lambda: calls.append("a"), interval_ms=0)
    scheduler = scheduler_module.run([task])

    assert calls == []  # constructing the generator runs no code yet
    next(scheduler)
    assert calls == ["a"]
    next(scheduler)
    assert calls == ["a", "a"]


def test_yield_counts_only_periodic_fires_not_interval_zero(
    scheduler_module, fake_utime
):
    fake_utime.now = 0
    always_on = scheduler_module.Task(lambda: None, interval_ms=0)
    scheduler = scheduler_module.run([always_on])

    round_count = next(scheduler)

    assert round_count == 0  # interval_ms=0 fires every round but carries
    # no information about whether the round was "busy"


def test_yield_counts_a_periodic_task_that_fired(scheduler_module, fake_utime):
    fake_utime.now = 0
    periodic = scheduler_module.Task(lambda: None, interval_ms=10)
    fake_utime.now = 10
    scheduler = scheduler_module.run([periodic])

    round_count = next(scheduler)

    assert round_count >= 1


def test_bare_next_caller_still_works_ignoring_the_yield_value(
    scheduler_module, fake_utime
):
    calls = []
    fake_utime.now = 0
    task = scheduler_module.Task(lambda: calls.append("a"), interval_ms=0)

    next(scheduler_module.run([task]))  # must not raise despite new yield value

    assert calls == ["a"]
