"""Per-user storage for reusable HTTP request history."""
import json
import os
import tempfile
import uuid

APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "tpfireman")
STORE_PATH = os.path.join(APP_DIR, "request_history.json")


def _read():
    """Load saved requests, returning an empty list when no history exists."""
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as stream:
            requests = json.load(stream)
        if not isinstance(requests, list):
            raise ValueError
        return requests
    except FileNotFoundError:
        return []
    except (ValueError, OSError) as exc:
        raise RuntimeError("Request history is unreadable or damaged.") from exc


def _write(requests):
    """Persist request history atomically in the per-user data directory."""
    os.makedirs(APP_DIR, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="request_history_", suffix=".tmp", dir=APP_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(requests, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, STORE_PATH)
    finally:
        if os.path.exists(temp):
            os.remove(temp)


def save_request(method, url, payload, export, request_id=None, label=None):
    """Add or update a saved request, avoiding duplicate method/URL entries."""
    requests = _read()
    existing = None
    if request_id:
        existing = next((item for item in requests if item.get("id") == request_id), None)
    if existing is None:
        existing = next((item for item in requests if item.get("method") == method and item.get("url") == url), None)
    if existing is None:
        existing = {"id": uuid.uuid4().hex[:12]}
        requests.append(existing)
    if label is None:
        label = existing.get("label") or url
    existing.update({"method": method, "url": url, "label": label, "payload": payload, "export": bool(export)})
    _write(requests)
    return existing


def resolve_request(reference, requests=None):
    """Find a request by ID or case-insensitive URL/name."""
    requests = _read() if requests is None else requests
    matches = [item for item in requests if item.get("id") == reference or item.get("label", item.get("name", "")).casefold() == reference.casefold() or item.get("url", "").casefold() == reference.casefold()]
    if len(matches) != 1:
        raise ValueError("No unique history entry matches that ID or name.")
    return matches[0]


def _delete_requests(references, requests):
    """Delete selected request entries after resolving every reference uniquely."""
    resolved = []
    for reference in references:
        item = resolve_request(reference, requests)
        if item not in resolved:
            resolved.append(item)
    if not resolved:
        raise ValueError("Provide at least one history ID or label to delete.")
    import main
    confirm = main.read_interactive("Delete {} history entr{}? (y/n): ".format(len(resolved), "y" if len(resolved) == 1 else "ies")).strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return
    for item in resolved:
        requests.remove(item)
    _write(requests)
    print("History entr{} deleted.".format("y" if len(resolved) == 1 else "ies"))


def history_command(args):
    """Handle history management commands and run selected saved requests."""
    if not args or args[0].casefold() != "history":
        return False
    try:
        requests = _read()
        if len(args) > 1 and args[1].casefold() == "edit":
            if len(args) != 3:
                raise ValueError("Usage: tpfireman history edit <id-or-label-or-url>")
            selected = resolve_request(args[2], requests)
            _review_and_run(selected, run_request=False)
            return True
        if len(args) > 1 and args[1].casefold() in {"delete", "remove"}:
            refs = args[2:]
            if not refs:
                raise ValueError("Usage: tpfireman history delete <id-or-label> [id-or-label ...]")
            _delete_requests(refs, requests)
            return True
        if len(args) > 1:
            if args[1].casefold() in {"list", "show"}:
                if len(args) != 2:
                    raise ValueError("Usage: tpfireman history list")
            else:
                selected = resolve_request(args[1], requests)
                _review_and_run(selected)
                return True
        if not requests:
            print("No saved requests.")
            return True
        for item in requests:
            label = item.get("label", item.get("name", item["url"]))
            shown_label = "" if label == item["url"] else "  [{}]".format(label)
            print("{}  {}  {}{}  export={}".format(item["id"], item["method"], item["url"], shown_label, str(item.get("export", False)).lower()))
        if len(args) > 1:
            return True
        import main
        reference = main.read_interactive("Select request by ID or URL/name (or leave blank to cancel): ").strip()
        if not reference:
            return True
        _review_and_run(resolve_request(reference, requests))
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        print("History error: {}".format(exc))
    return True


def _review_and_run(item, run_request=True):
    """Prompt to review saved request fields, save changes, and optionally invoke main."""
    import main
    method = main.read_interactive("Method [{}]: ".format(item["method"])).strip() or item["method"]
    url = main.read_interactive("URL [{}]: ".format(item["url"])).strip() or item["url"]
    current_label = item.get("label", item.get("name", item["url"]))
    label = main.read_interactive("Label [{}] (type = to use URL): ".format("=" if current_label == item["url"] else current_label)).strip()
    if not label:
        label = current_label
    elif label == "=":
        label = url
    payload = item.get("payload")
    payload_text = "" if payload is None else json.dumps(payload, ensure_ascii=False)
    entered = main.read_interactive("JSON payload [{}] (type - to clear): ".format(payload_text)).strip()
    if entered == "-":
        payload = None
    elif entered:
        lines = [entered]
        while True:
            line = main.read_interactive()
            if not line:
                break
            lines.append(line)
        payload = json.loads(" ".join(lines))
    export_default = "y" if item.get("export", False) else "n"
    export = main.read_interactive("Export response? (y/n) [{}]: ".format(export_default)).strip().lower() or export_default
    if export not in {"y", "n"}:
        raise ValueError("Export choice must be y or n.")
    updated = save_request(method.upper(), url, payload, export == "y", item["id"], label=label)
    if run_request:
        main.main([updated["method"], updated["url"], "TRUE" if updated["export"] else "FALSE"], show_banner=False,
                  guided_payload=json.dumps(updated["payload"], ensure_ascii=False) if updated["payload"] is not None else None,
                  guided_payload_set=updated["payload"] is not None, history_id=updated["id"])
    else:
        print("History entry updated.")
