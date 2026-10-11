"""Per-user default HTTP timeout configuration."""
import json
import os
import tempfile

APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "tpfireman")
STORE_PATH = os.path.join(APP_DIR, "request_timeout.json")
DEFAULT_TIMEOUT = 300.0


def _validate(value):
    try:
        seconds = float(value)
        if seconds <= 0 or not seconds < float("inf"):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Timeout must be a positive number of seconds.")
    return seconds


def get_timeout():
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as stream:
            data = json.load(stream)
        return _validate(data["seconds"])
    except FileNotFoundError:
        return DEFAULT_TIMEOUT
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("Saved timeout is unreadable or damaged; use 'tpfireman timeout edit' to replace it.") from exc


def set_timeout(value):
    seconds = _validate(value)
    os.makedirs(APP_DIR, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="request_timeout_", suffix=".tmp", dir=APP_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"seconds": seconds}, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, STORE_PATH)
    finally:
        if os.path.exists(temp):
            os.remove(temp)
    return seconds


def timeout_command(args):
    if not args or args[0].casefold() != "timeout":
        return False
    import main
    try:
        action = args[1].casefold() if len(args) > 1 else "show"
        if action == "show" and len(args) == 2:
            seconds = get_timeout()
            print("Current request timeout: {:g} seconds ({:g} minutes).".format(seconds, seconds / 60))
        elif action == "edit" and len(args) in (2, 3):
            value = args[2] if len(args) == 3 else main.read_interactive("Timeout in seconds: ").strip()
            print("Request timeout saved: {:g} seconds.".format(set_timeout(value)))
        elif action == "delete" and len(args) == 2:
            print("Warning: deleting the saved timeout will restore the default of 5 minutes (300 seconds).")
            if main.read_interactive("Continue? (y/n): ").strip().casefold() == "y":
                try:
                    os.remove(STORE_PATH)
                except FileNotFoundError:
                    pass
                print("Saved timeout removed. Default restored: 300 seconds (5 minutes).")
            else:
                print("Cancelled; timeout unchanged.")
        else:
            raise ValueError("Usage: tpfireman timeout [show|edit [SECONDS]|delete]")
    except (ValueError, RuntimeError, OSError) as exc:
        print("Timeout error: {}".format(exc))
    return True
