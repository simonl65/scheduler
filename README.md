# MicroPython Cooperative Scheduler

A simple, lightweight, cooperative scheduler module designed for MicroPython.

[![License](https://img.shields.io/badge/license-SUL--1.0-green.svg)](LICENSE.md)

## Installation

### Via `mip`

You can install this package directly onto your MicroPython device using `mip`:

```python
import mip
mip.install("github:simonl65/scheduler")
```

Or using `mpremote`:

```bash
mpremote mip install github:simonl65/scheduler
```

### Via `uv` / `pip` (For development/simulation)

For local simulation or development, you can install the package via:

```bash
uv pip install .
# or
pip install .
```

## Usage

Define your task functions and task list, and run the scheduler loop:

```python
from machine import Pin
from scheduler import Task, run

led = Pin("LED", Pin.OUT)

def task_led():
    led.toggle()
    print("LED toggled")

def task_sensor():
    print("Reading sensor data")

# Set up tasks with their intervals (in milliseconds)
tasks = [
    Task(task_led, interval_ms=1000),
    Task(task_sensor, interval_ms=500),
]

# Run the scheduler
# Setting light_sleep=True will sleep between task rounds to save power
scheduler = run(tasks, light_sleep=True)

while True:
    next(scheduler)
```
