import sys
from unittest.mock import MagicMock

from scheduler import Task, run

# Mock MicroPython modules before importing scheduler
mock_utime = MagicMock()
mock_machine = MagicMock()

# Setup default behaviors for ticks_diff and ticks_ms
current_time_ms = 0


def mock_ticks_ms():
    return current_time_ms


def mock_ticks_diff(t1, t2):
    return t1 - t2


mock_utime.ticks_ms = mock_ticks_ms
mock_utime.ticks_diff = mock_ticks_diff

sys.modules["utime"] = mock_utime
sys.modules["machine"] = mock_machine


def test_task_init():
    task_func = MagicMock()
    task = Task(task_func, interval_ms=100)
    assert task.task_to_run == task_func
    assert task.interval_ms == 100
    assert task.last_ms == 0


def test_scheduler_runs_due_tasks():
    global current_time_ms
    current_time_ms = 0

    task_func1 = MagicMock()
    task_func2 = MagicMock()

    task1 = Task(task_func1, interval_ms=100)
    task2 = Task(task_func2, interval_ms=200)

    scheduler = run([task1, task2])

    # First tick at 0 ms: since last_ms is 0, ticks_diff(0, 0) is 0.
    # task1: interval 100, ticks_diff(0, 0) = 0 < 100 -> not run
    # task2: interval 200, ticks_diff(0, 0) = 0 < 200 -> not run
    next(scheduler)
    task_func1.assert_not_called()
    task_func2.assert_not_called()

    # Advance time to 100 ms
    current_time_ms = 100
    next(scheduler)
    task_func1.assert_called_once()
    task_func2.assert_not_called()

    # Reset call counts
    task_func1.reset_mock()

    # Advance time to 150 ms
    current_time_ms = 150
    next(scheduler)
    task_func1.assert_not_called()
    task_func2.assert_not_called()

    # Advance time to 200 ms
    current_time_ms = 200
    next(scheduler)
    # task1 last run was at 100ms, diff is 200 - 100 = 100 >= 100 -> runs again
    # task2 last run was at 0ms, diff is 200 - 0 = 200 >= 200 -> runs
    task_func1.assert_called_once()
    task_func2.assert_called_once()


def test_scheduler_light_sleep():
    global current_time_ms
    current_time_ms = 0

    task_func = MagicMock()
    task = Task(task_func, interval_ms=150)

    # run with light_sleep=True
    scheduler = run([task], light_sleep=True)

    mock_machine.lightsleep.reset_mock()
    next(scheduler)

    # min_sleep_ms is 1, task.interval_ms is 150. min of tasks intervals is 150.
    # sleep_for should be max(1, 150) = 150.
    mock_machine.lightsleep.assert_called_once_with(150)
