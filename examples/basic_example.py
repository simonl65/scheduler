"""
Basic example usage of the cooperative scheduler module.
"""

from machine import Pin  # type: ignore

from scheduler.scheduler import Task, run

led = Pin("LED", Pin.OUT)


# =============================================================================
# TASKS
# =============================================================================
def toggle_led():
    led.toggle()  # type: ignore
    print("toggle LED or similar")


def read_sensor():
    print("read sensor")


def update_display():
    print("update display")


# =============================================================================
# Initialize hardware
# =============================================================================
def init():
    print("Hardware initialised, ready to run tasks")


# =============================================================================
# Safe shutdown procedure
# =============================================================================
def safe_shutdown():
    print("Performing safe shutdown...")
    # Add any necessary cleanup code here (e.g., turn off peripherals, save state)
    led.off()


# =============================================================================
# Task list: (function, interval_ms)
# Order determines priority — first entry has highest priority.
# =============================================================================
tasks = [
    Task(toggle_led, interval_ms=2000),
    Task(read_sensor, interval_ms=50),
    Task(update_display, interval_ms=500),
]


# =============================================================================
# Entry point
# Set light_sleep=True to let the device sleep between task rounds.
# The scheduler will sleep for up to the shortest task interval each round,
# waking early if needed. Uses machine.lightsleep() — state is preserved.
# =============================================================================
if __name__ == "__main__":
    try:
        init()

        while True:
            # Run the generator-based scheduler loop
            # light_sleep=True saves power by sleeping when there are no tasks due.
            next(run(tasks, light_sleep=True))

    except KeyboardInterrupt:
        safe_shutdown()
        print("Stopped by user")
