
import sys
import urllib.request
import urllib.parse
import json
import os
import getpass
import re
from auth_store import auth_command, select_auth_headers
from datetime import datetime
from urllib.parse import urlsplit

# ANSI Color Codes
WHITE = "\033[97m"
RED = "\033[31m"
RESET = "\033[0m"
YELLOW = "\033[93m"
CYAN = "\033[96m"

def print_logo():
    print(f"{CYAN}")
    print(r"""
    _______  _____  __  __  _   _  _____  _   _  _   _  _____  _   _  
    |__   __|  _  ||  \/  || | | ||  ___|| | | ||  \  ||  ___|| | | | 
       | |  | | | || |\/| || | | || |___ | |_| || |\/| || |___|| | | |
       | |  | |_| || |  | || | | |||___  ||     || |  | |||___  ||     |
       |_|  |_____||_|\__| |_| |_||_____||_|\__| |_|\__| |_____||_|\__|
    """ )
    print(f"{WHITE}  --- API Testing Client ---{RESET}")
    print(f'{CYAN}Type "help" for usage instructions.{RESET}\n')

def check_admin():
    # Check whether this process has an elevated Windows token.
    if sys.platform != "win32":
        return

    try:
        import ctypes
        from ctypes import wintypes

        TOKEN_QUERY = 0x0008
        TOKEN_ELEVATION_CLASS = 20

        class TOKEN_ELEVATION(ctypes.Structure):
            _fields_ = [("TokenIsElevated", wintypes.DWORD)]

        token = wintypes.HANDLE()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.restype = wintypes.HANDLE
        open_process_token = advapi32.OpenProcessToken
        open_process_token.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        open_process_token.restype = wintypes.BOOL
        get_token_information = advapi32.GetTokenInformation
        get_token_information.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        get_token_information.restype = wintypes.BOOL
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL

        if not open_process_token(get_current_process(), TOKEN_QUERY, ctypes.byref(token)): 
            raise ctypes.WinError()

        try:
            elevation = TOKEN_ELEVATION()
            returned_length = wintypes.DWORD()
            if not get_token_information(
                token,
                TOKEN_ELEVATION_CLASS,
                ctypes.byref(elevation),
                ctypes.sizeof(elevation),
                ctypes.byref(returned_length),
            ):
                raise ctypes.WinError()
            is_elevated = bool(elevation.TokenIsElevated)
        finally:
            close_handle(token)
    except Exception as exc:
        print(f"{YELLOW}WARNING: Could not determine whether this process is elevated: {exc}{RESET}")
        return

    if is_elevated:
        print(f"{RED}WARNING: This command should NOT be executed as Administrator.{RESET}")
        print(f"{RED}Please run a standard terminal session and try again.{RESET}")
        sys.exit(1)

def export_response(method, url, response_data, status_code, filename):
    filename = os.path.abspath(os.path.expanduser(filename))
    if os.path.exists(filename):
        confirm = input("File already exists: {}. Overwrite? (y/n): ".format(filename)).strip().lower()
        if confirm != "y":
            print("Export cancelled; existing file was not changed.")
            return None

    data = response_data if isinstance(response_data, str) else response_data.decode("utf-8", errors="replace")
    try:
        data = json.dumps(json.loads(data), indent=2, ensure_ascii=False)
    except ValueError:
        pass

    directory = os.path.dirname(filename)
    if not os.path.isdir(directory):
        raise OSError("Export directory does not exist.")
    # Use exclusive creation when the target did not exist, so a concurrent creation
    # cannot be silently overwritten after the existence check.
    mode = "x" if not os.path.exists(filename) else "w"
    try:
        with open(filename, mode, encoding="utf-8") as stream:
            stream.write("Method: {}\\n".format(method))
            stream.write("URL: {}\\n".format(url))
            stream.write("Status Code: {}\\n".format(status_code))
            stream.write("Timestamp: {}\\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            stream.write("-" * 50 + "\\n")
            stream.write(data)
    except FileExistsError:
        raise OSError("The export file appeared after confirmation; no file was overwritten.")
    return filename

def redact_text(text, secrets_to_hide):
    for secret in sorted((value for value in secrets_to_hide if value), key=len, reverse=True):
        text = text.replace(secret, "[REDACTED]")
    return text


def print_http_response(status_code, headers, raw_data, secrets_to_hide):
    color = RED if status_code >= 400 else WHITE
    print("{}Status Code: {}{}".format(color, status_code, RESET))
    print("{}Headers:{}".format(WHITE, RESET))
    for key, value in headers.items():
        print("  {}: {}".format(key, redact_text(value, secrets_to_hide)))
    print("\n{}Response Body:{}".format(WHITE, RESET))
    try:
        body = json.dumps(json.loads(raw_data), indent=2, ensure_ascii=False)
    except ValueError:
        body = raw_data
    print(redact_text(body, secrets_to_hide))


def main():
    if auth_command(sys.argv[1:]):
        return
    print_logo()
    check_admin()

    if len(sys.argv) < 3:
        print(f"{YELLOW}Usage: tpfireman <METHOD> <URL> [EXPORT:TRUE|FALSE] [PAYLOAD:JSON_STRING]{RESET}")
        print(f"Methods: GET, POST, PUT, DELETE, PATCH")
        print(f"Example: tpfireman POST https://api.example.com/data")
        sys.exit(1)

    method = sys.argv[1].strip().upper()
    url = sys.argv[2].strip()

    supported_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
    if method not in supported_methods:
        print(f"{RED}Error: Unsupported HTTP method '{method}'. Supported methods: GET, POST, PUT, DELETE, PATCH.{RESET}")
        sys.exit(1)

    try:
        parsed_url = urlsplit(url)
        if parsed_url.scheme.lower() not in {"http", "https"} or not parsed_url.netloc or not parsed_url.hostname:
            raise ValueError
        # Accessing port validates its numeric range and syntax.
        parsed_url.port
    except ValueError:
        print(f"{RED}Error: Invalid URL. Provide an absolute HTTP or HTTPS URL with a valid host and port.{RESET}")
        sys.exit(1)

    export_mode = False
    timeout_seconds = 10
    positional_args = sys.argv[3:]
    while positional_args and positional_args[0].startswith("--"):
        option = positional_args.pop(0)
        if option != "--timeout" or not positional_args:
            print(f"{RED}Error: Unknown or incomplete option '{option}'. Use --timeout SECONDS.{RESET}")
            sys.exit(1)
        timeout_value = positional_args.pop(0)
        try:
            timeout_seconds = float(timeout_value)
            if timeout_seconds <= 0 or not timeout_seconds < float("inf"):
                raise ValueError
        except ValueError:
            print(f"{RED}Error: Timeout must be a positive number of seconds.{RESET}")
            sys.exit(1)

    if positional_args:
        export_arg = positional_args.pop(0).strip().upper()
        if export_arg not in {"TRUE", "FALSE"}:
            print(f"{RED}Error: Invalid export option '{export_arg}'. Use TRUE or FALSE.{RESET}")
            sys.exit(1)
        export_mode = export_arg == "TRUE"
    if positional_args:
        print(f"{RED}Error: Unexpected extra arguments. The JSON payload is entered interactively.{RESET}")
        sys.exit(1)

    # Select a stored authentication profile; secret values are never displayed.
    try:
        request_headers, secrets_to_hide, authenticated_url = select_auth_headers(url)
        url = authenticated_url
    except Exception as exc:
        print(f"{RED}Authentication error: {type(exc).__name__}; details suppressed to protect credentials.{RESET}")
        sys.exit(1)

    # Headers are entered interactively so credentials are not exposed in command history.
    while input(f"{YELLOW}Add a custom HTTP header? (y/n): {RESET}").strip().lower() == "y":
        name = input(f"{YELLOW}Header name: {RESET}").strip()
        if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name):
            print(f"{RED}Error: Invalid HTTP header name.{RESET}")
            sys.exit(1)
        value = getpass.getpass(f"{YELLOW}Header value (hidden; use for Authorization credentials): {RESET}")
        if any(char in value for char in "\\r\\n"):
            print(f"{RED}Error: Header values cannot contain line breaks.{RESET}")
            sys.exit(1)
        if name.lower() in {key.lower() for key in request_headers}:
            print(f"{RED}Error: Duplicate HTTP header '{name}'.{RESET}")
            sys.exit(1)
        request_headers[name] = value
        if value:
            secrets_to_hide.append(value)
        if name.lower() == "authorization":
            secrets_to_hide.extend(value.split())

    # Prepare Request
    payload = None
    payload_methods = ["POST", "PUT", "PATCH"]
    
    # If no payload is provided via command line and it is a method that supports it
    if method in payload_methods and len(sys.argv) == 3:
        ans = input(f"{YELLOW}Do you want to provide a JSON payload? (y/n): {RESET}").lower()
        if ans == "y":
            payload_str = input(f"{YELLOW}Paste your JSON payload here: {RESET}")
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                print(f"{RED}Error: Invalid JSON provided.{RESET}")
                sys.exit(1)

    try:
        # Create request object
        req = urllib.request.Request(url, method=method)
        
        # Add common headers
        req.add_header("User-Agent", "API-Testing-Client")
        for header_name, header_value in request_headers.items():
            req.add_header(header_name, header_value)
        if payload:
            req.data = json.dumps(payload).encode("utf-8")
            req.add_header("Content-Type", "application/json")
        
        try:
            response = urllib.request.urlopen(req, timeout=timeout_seconds)
        except urllib.error.HTTPError as http_error:
            # HTTPError is also a response: handle it with the same status/header/body format.
            response = http_error

        with response:
            status_code = response.getcode()
            raw_data = response.read().decode("utf-8", errors="replace")
            response_headers = response.headers

        print_http_response(status_code, response_headers, raw_data, secrets_to_hide)
        if status_code >= 400:
            sys.exit(1)

        # Export if requested
        if export_mode:
            export_path = input("Export file path (default: api_response.txt): ").strip()
            if not export_path:
                export_path = "api_response.txt"
            response_path = export_response(
                method,
                redact_text(url, secrets_to_hide),
                redact_text(raw_data, secrets_to_hide),
                status_code,
                export_path,
            )
            if response_path:
                print(f"\n{WHITE}Response exported to {response_path}{RESET}")

    except Exception as e:
        if isinstance(e, TimeoutError):
            print(f"{RED}Error: Request timed out after {timeout_seconds:g} seconds.{RESET}")
        else:
            print(f"{RED}Error: {type(e).__name__}; details suppressed to protect credentials.{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()

