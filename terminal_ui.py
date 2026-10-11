"""Small, dependency-free terminal styling helpers."""
import os
import sys
import threading
import time


_COLOR_ENABLED = sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM", "") != "dumb"

RESET = "\033[0m" if _COLOR_ENABLED else ""
CYAN = "\033[96m" if _COLOR_ENABLED else ""
BLUE = "\033[94m" if _COLOR_ENABLED else ""
GREEN = "\033[92m" if _COLOR_ENABLED else ""
YELLOW = "\033[93m" if _COLOR_ENABLED else ""
DIM = "\033[2m" if _COLOR_ENABLED else ""
BOLD = "\033[1m" if _COLOR_ENABLED else ""


def paint(text, color):
    return "{}{}{}".format(color, text, RESET)


def panel(title, rows, color=CYAN):
    """Print a compact, readable titled panel from (command, description) rows."""
    rows = list(rows)
    command_width = min(max((len(command) for command, _ in rows), default=0), 48)
    print(paint("┌─ {}".format(title), color))
    for command, description in rows:
        print("│  {}  {}".format(paint(command.ljust(command_width), BOLD), paint(description, DIM)))
    print(paint("└" + "─" * 72, color))


def section(title):
    print(paint(title, BOLD + CYAN))


class RequestLoader:
    """Animated request indicator that stays silent for redirected output."""

    _FRAMES = ("◜", "◠", "◝", "◞", "◡", "◟")
    _BAR = ("▰", "▱", "▱", "▱", "▱", "▱", "▱", "▱", "▱", "▱")

    def __init__(self, label="Sending request"):
        self.label = label
        self.enabled = _COLOR_ENABLED
        self._stop = threading.Event()
        self._thread = None
        self._start = None

    def __enter__(self):
        if self.enabled:
            self._start = time.monotonic()
            self._thread = threading.Thread(target=self._animate, daemon=True)
            self._thread.start()
        return self

    def _animate(self):
        index = 0
        while not self._stop.wait(0.1):
            elapsed = time.monotonic() - self._start
            bar = list(self._BAR)
            bar[index % len(bar)] = "▰"
            frame = self._FRAMES[index % len(self._FRAMES)]
            line = "\r{} {} {} {} {:.1f}s{}".format(CYAN, frame, self.label, "".join(bar), elapsed, RESET)
            sys.stdout.write(line)
            sys.stdout.flush()
            index += 1

    def __exit__(self, exc_type, exc_value, traceback):
        if self.enabled:
            self._stop.set()
            self._thread.join()
            sys.stdout.write("\r" + " " * (len(self.label) + 32) + "\r")
            sys.stdout.flush()
