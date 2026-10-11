"""Encrypted, per-user authentication profile storage for Windows."""
import base64
import ctypes
import json
import os
import sys
import tempfile
import uuid
from ctypes import wintypes

APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "tpfireman")
STORE_PATH = os.path.join(APP_DIR, "auth_profiles.json")
AUTH_TYPES = ("Bearer", "Basic", "API key", "OAuth2 Client Credentials", "OAuth2 Authorization Code (PKCE)")


def _crypt(value, decrypt=False):
    """Protect or unprotect UTF-8 secrets with DPAPI for the current Windows user."""
    if sys.platform != "win32":
        raise RuntimeError("Authentication secrets require Windows DPAPI.")

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    # DPAPI returns allocated memory; retain the input buffer for the full native call.
    raw = value if decrypt else value.encode("utf-8")
    source_buffer = ctypes.create_string_buffer(raw)
    source = DATA_BLOB(len(raw), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    result = DATA_BLOB()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [ctypes.POINTER(DATA_BLOB), wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        ok = crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(result))
    else:
        ok = crypt32.CryptProtectData(ctypes.byref(source), "tpfireman auth", None, None, None, 0, ctypes.byref(result))
    if not ok:
        raise RuntimeError("Windows DPAPI operation failed; verify the current Windows account and profile.")
    try:
        # Store encrypted bytes as base64 text; always release DPAPI's output buffer.
        output = ctypes.string_at(result.pbData, result.cbData)
        return output if decrypt else base64.b64encode(output).decode("ascii")
    finally:
        kernel32.LocalFree(result.pbData)


def _read():
    """Load the profile list, treating a missing store as an empty collection."""
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data, list):
            raise ValueError
        return data
    except FileNotFoundError:
        return []
    except (ValueError, OSError) as exc:
        raise RuntimeError("Authentication store is unreadable or damaged.") from exc


def _write(profiles):
    """Persist profiles through an atomic replacement to avoid partial JSON files."""
    os.makedirs(APP_DIR, exist_ok=True)
    # Create the temporary file beside the target so replacement stays on one volume.
    fd, temp = tempfile.mkstemp(prefix="auth_profiles_", suffix=".tmp", dir=APP_DIR)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(profiles, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, STORE_PATH)
    if sys.platform == "win32":
        import ctypes
        if not ctypes.windll.kernel32.SetFileAttributesW(STORE_PATH, 0x2):
            raise ctypes.WinError()


def _secret(profile):
    """Decode a profile's encrypted secret payload into its field dictionary."""
    return json.loads(_crypt(base64.b64decode(profile["secret"]), decrypt=True).decode("utf-8"))


def _save_secret(profile, values):
    """Serialize profile fields and encrypt them before adding them to the store."""
    profile["secret"] = _crypt(json.dumps(values, ensure_ascii=False))


def _prompt(label, hidden=False, allow_empty=False):
    """Prompt for required or optional input, hiding values when requested."""
    import getpass
    while True:
        value = (getpass.getpass if hidden else input)(label).strip()
        if value or allow_empty:
            return value
        print("This value is required.")


def _collect(kind, existing=None):
    """Collect and validate the fields required by an authentication profile type."""
    old = existing or {}
    values = {}
    def ask(key, label, secret=False, optional=False):
        prior = old.get(key, "")
        prompt = label + (" (press Enter to keep current value)" if prior else "") + ": "
        entered = _prompt(prompt, secret, allow_empty=bool(prior or optional))
        values[key] = entered if entered else prior
    if kind == "Bearer":
        ask("token", "Bearer token", True)
    elif kind == "Basic":
        ask("username", "Username", True)
        ask("password", "Password", True)
    elif kind == "API key":
        ask("header", "Header name (e.g. X-API-Key)")
        ask("location", "Location (header/query)")
        if values["location"].lower() not in ("header", "query"):
            raise ValueError("API key location must be header or query.")
        ask("key", "API key", True)
    elif kind == "OAuth2 Client Credentials":
        ask("token_url", "Token endpoint URL")
        ask("client_id", "Client ID")
        ask("client_secret", "Client secret", True)
        ask("scope", "Scope (optional)", optional=True)
        ask("header", "Token header (default Authorization)", optional=True)
        ask("prefix", "Token prefix (default Bearer)", optional=True)
    elif kind == "OAuth2 Authorization Code (PKCE)":
        ask("authorization_url", "Authorization endpoint URL")
        ask("token_url", "Token endpoint URL")
        ask("client_id", "Client ID")
        ask("redirect_uri", "Redirect URI (e.g. http://127.0.0.1:8765/callback)")
        ask("scope", "Scope (optional)", optional=True)
        ask("header", "Token header (default Authorization)", optional=True)
        ask("prefix", "Token prefix (default Bearer)", optional=True)
    # Require HTTPS for OAuth endpoints; permit HTTP only for a loopback PKCE callback.
    for field in ("token_url", "authorization_url", "redirect_uri"):
        if field in values:
            parsed = urllib.parse.urlsplit(values[field])
            if parsed.scheme.lower() != "https" and not (field == "redirect_uri" and parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1")):
                raise ValueError("OAuth endpoints must use HTTPS; only the localhost PKCE callback may use HTTP.")
            if not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("OAuth URL must include a valid host and no embedded credentials.")
    if kind.startswith("OAuth2") and (values.get("header") or "Authorization").lower() == "authorization":
        values["prefix"] = values.get("prefix") or "Bearer"
    return values


def _profile_by(ref, profiles):
    """Resolve a profile by exact ID or case-insensitive name, requiring one match."""
    matches = [p for p in profiles if p["id"] == ref or p["name"].casefold() == ref.casefold()]
    if len(matches) != 1:
        raise ValueError("No unique profile matches that name or ID.")
    return matches[0]


def auth_command(args):
    """Run auth profile management commands. Return True if handled."""
    if len(args) < 2 or args[0].lower() != "auth":
        return False
    command = args[1].lower()
    try:
        profiles = _read()
        if command == "list":
            list_auth_profiles()
        elif command in ("delete", "remove"):
            if "--all" not in args[2:]:
                refs = args[2:]
                if not refs:
                    raise ValueError("Usage: tpfireman auth delete <name-or-id> [name-or-id ...] | --all")
                resolved = []
                for ref in refs:
                    profile = _profile_by(ref, profiles)
                    if profile not in resolved:
                        resolved.append(profile)
                if input("Delete {} authentication profile(s)? (y/n): ".format(len(resolved))).strip().lower() != "y":
                    print("Cancelled.")
                    return True
                for profile in resolved:
                    profiles.remove(profile)
                _write(profiles)
                print("Authentication profile(s) deleted.")
                return True
            refs = args[2:]
            if refs != ["--all"]:
                raise ValueError("Use --all by itself for bulk deletion.")
            confirm = input("Delete ALL saved authentication profiles? (y/n): ").strip().lower()
            if confirm != "y":
                print("Cancelled.")
                return True
            profiles = []
            _write(profiles)
            print("Authentication profile(s) deleted.")
        elif command == "rename":
            if len(args) != 4:
                raise ValueError("Usage: tpfireman auth rename <name-or-id> <new-name>")
            profile = _profile_by(args[2], profiles)
            if any(p is not profile and p["name"].casefold() == args[3].casefold() for p in profiles):
                raise ValueError("That profile name is already in use.")
            profile["name"] = args[3]
            _write(profiles)
            print("Authentication profile renamed.")
        elif command in ("add", "edit"):
            if command == "edit":
                if len(args) != 3:
                    raise ValueError("Usage: tpfireman auth edit <name-or-id>")
                profile = _profile_by(args[2], profiles)
                kind = profile["type"]
                values = _collect(kind, _secret(profile))
                _save_secret(profile, values)
                _write(profiles)
                print("Authentication profile updated.")
            else:
                if len(args) != 2:
                    raise ValueError("Usage: tpfireman auth add")
                print("Authentication type:")
                for number, kind in enumerate(AUTH_TYPES, 1):
                    print("{}. {}".format(number, kind))
                choice = _prompt("Select type: ")
                if not choice.isdigit() or not 1 <= int(choice) <= len(AUTH_TYPES):
                    raise ValueError("Invalid authentication type.")
                kind = AUTH_TYPES[int(choice) - 1]
                name = _prompt("Configuration name: ")
                if any(p["name"].casefold() == name.casefold() for p in profiles):
                    raise ValueError("That profile name is already in use.")
                profile = {"id": uuid.uuid4().hex[:12], "name": name, "type": kind}
                _save_secret(profile, _collect(kind))
                profiles.append(profile)
                _write(profiles)
                print("Authentication profile saved (ID: {}).".format(profile["id"]))
        else:
            print("Usage: tpfireman auth <add|list|edit|rename|delete>")
    except (ValueError, RuntimeError, OSError) as exc:
        print("Error: {}".format(exc) if isinstance(exc, ValueError) else "Error: Authentication operation failed; details suppressed.")
    return True


def _oauth_token(values, code_flow=False):
    """Obtain an access token with client credentials or the PKCE authorization flow."""
    import hashlib
    import secrets
    import threading
    import webbrowser
    from http.server import BaseHTTPRequestHandler, HTTPServer
    if not code_flow:
        body = {"grant_type": "client_credentials", "client_id": values["client_id"], "client_secret": values["client_secret"]}
        if values.get("scope"):
            body["scope"] = values["scope"]
        request = urllib.request.Request(values["token_url"], data=urllib.parse.urlencode(body).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())["access_token"]

    parsed = urllib.parse.urlsplit(values["redirect_uri"])
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("PKCE callback must use http://localhost or http://127.0.0.1.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("PKCE redirect URI cannot include credentials, query parameters, or fragments.")
    port = parsed.port or 80
    # PKCE binds the authorization code to this client; state protects against CSRF.
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)
    result = {}
    # Accept one local redirect callback and validate its path and state parameter.
    class CallbackHTTPServer(HTTPServer):
        allow_reuse_address = True
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed_callback = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(parsed_callback.query)
            if parsed_callback.path != callback_path:
                self.send_error(404)
                return
            if query.get("state", [None])[0] != state:
                result["error"] = "Invalid OAuth state"
            else:
                result["code"] = query.get("code", [None])[0]
                result["error"] = query.get("error", [None])[0]
            self.send_response(200); self.end_headers(); self.wfile.write(b"Authentication received. You may close this browser tab.")
        def log_message(self, *args):
            # Avoid writing callback URLs, which may contain sensitive authorization data.
            pass
    callback_path = parsed.path or "/"
    server = CallbackHTTPServer((parsed.hostname, port), Handler)
    server.timeout = 180
    query = {"response_type": "code", "client_id": values["client_id"], "redirect_uri": values["redirect_uri"], "code_challenge": challenge, "code_challenge_method": "S256", "state": state}
    if values.get("scope"):
        query["scope"] = values["scope"]
    webbrowser.open(values["authorization_url"] + ("&" if "?" in values["authorization_url"] else "?") + urllib.parse.urlencode(query))
    server.handle_request(); server.server_close()
    if not result.get("code"):
        raise ValueError("OAuth authorization did not complete.")
    body = {"grant_type": "authorization_code", "client_id": values["client_id"], "redirect_uri": values["redirect_uri"], "code": result["code"], "code_verifier": verifier}
    request = urllib.request.Request(values["token_url"], data=urllib.parse.urlencode(body).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())["access_token"]


def list_auth_profiles():
    """Display saved authentication profiles without revealing secret values."""
    profiles = _read()
    if not profiles:
        print("No saved authentication profiles.")
        return
    print("Saved authentication profiles:")
    for profile in profiles:
        print("  {}  {} ({})".format(profile["id"], profile["name"], profile["type"]))


def select_auth_headers(url, profile_ref=None):
    """Apply a selected profile and return headers, redaction values, and request URL."""
    profiles = _read()
    if profile_ref:
        profile = _profile_by(profile_ref, profiles)
    else:
        if not profiles or input("Use a saved authentication profile? (y/n): ").strip().lower() != "y":
            return {}, [], url
        for number, profile in enumerate(profiles, 1):
            print("{}. {} ({})".format(number, profile["name"], profile["type"]))
        choice = _prompt("Select profile number: ")
        if not choice.isdigit() or not 1 <= int(choice) <= len(profiles):
            raise ValueError("Invalid profile selection.")
        profile = profiles[int(choice) - 1]
    values = _secret(profile)
    kind = profile["type"]
    headers, redact = {}, []
    if kind == "Bearer":
        token = values["token"]; headers["Authorization"] = "Bearer " + token; redact.append(token)
    elif kind == "Basic":
        token = base64.b64encode((values["username"] + ":" + values["password"]).encode()).decode()
        headers["Authorization"] = "Basic " + token; redact.extend((values["username"], values["password"], token))
    elif kind == "API key":
        key = values["key"]; redact.append(key)
        if values["location"].lower() == "header":
            headers[values["header"]] = key
        else:
            parts = urllib.parse.urlsplit(url)
            query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True) + [(values["header"], key)]
            url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query), parts.fragment))
    elif kind.startswith("OAuth2"):
        token = _oauth_token(values, "Authorization Code" in kind)
        header = values.get("header") or "Authorization"
        prefix = values.get("prefix") or "Bearer"
        headers[header] = (prefix + " " + token).strip(); redact.append(token)
    if kind == "Basic":
        headers["Authorization"] = "Basic " + base64.b64encode((values["username"] + ":" + values["password"]).encode()).decode()
    return headers, redact, url
