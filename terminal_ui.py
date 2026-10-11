"""Small, dependency-free terminal styling helpers."""
import os
import sys


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
