# tpfireman - API Testing Client

A lightweight, terminal-based API testing client for Windows.

## Features
- Support for common HTTP methods: GET, POST, PUT, DELETE, PATCH.
- Interactive JSON payload input for body-supported methods.
- Automatic Content-Type: application/json header handling.
- Response body pretty-printing (if JSON).
- Export response to a file with one flag.
- ANSI color support for better visibility.
- HTTPS support via Python's standard TLS handling in `urllib`.
- Reusable authentication profiles stored under `%LOCALAPPDATA%\\tpfireman\\auth_profiles.json`, with secrets encrypted by Windows DPAPI.
- Authentication types: Bearer, Basic, API key (header or query), OAuth2 Client Credentials, and OAuth2 Authorization Code with PKCE.
- Profile management: `tpfireman auth add|list|edit|rename|delete`; use `tpfireman auth delete --all` for confirmed bulk deletion. Values are never listed or echoed.

## Installation

To install tpfireman, you need to have [Python](https://www.python.org/downloads/) installed on your system. The updater uses the GitHub Releases API at `https://github.com/FoxEaterIT/tpfireman`.

1. Ensure Python 3.8 or newer is installed and available as `python` on PATH.
2. Open a **standard, non-elevated** PowerShell terminal in the directory containing the downloaded application files.
3. Run the installation script:
   ```powershell
   .\install.ps1
   ```
4. The installer copies the app to `%LOCALAPPDATA%\Programs\tpfireman`, prepares `%LOCALAPPDATA%\tpfireman` for user data, and adds the installed `bin` directory to the current user's PATH. No administrator privileges or third-party packages are required.
5. Restart your terminal to apply the PATH changes.

## Usage

Once installed, you can use the `tpfireman` command from anywhere in your terminal. `tpfireman version` displays the installed version, `tpfireman update` checks GitHub Releases and installs a newer release when available, and `tpfireman uninstall` starts the confirmed per-user uninstaller. The uninstaller removes the application, its exact PATH entry, and all tpfireman user data (including auth profiles).

The version is maintained in the root `VERSION` file (currently `0.1.0`) and copied during installation. Uninstallation removes the application, its PATH entry, and all tpfireman user data, including saved authentication profiles; this cannot be undone. Automatic updates check the latest GitHub Release at `FoxEaterIT/tpfireman` and expect a `tpfireman-source.zip` asset containing the application files and a matching `VERSION` file. Publish releases with tags such as `v1.2.3` and attach that ZIP asset; the updater asks for confirmation and preserves existing user data.

### Basic Syntax
```text
tpfireman <METHOD> <URL> [--timeout SECONDS] [EXPORT:TRUE|FALSE]
```

For `POST`, `PUT`, and `PATCH`, when no export argument is supplied, the client asks whether you want to enter a JSON payload interactively. Payloads are not currently accepted as command-line arguments. For each HTTP request, the client asks whether to use a saved authentication profile. Custom one-off headers can also be entered interactively with hidden values.

### Examples

**Simple GET request:**
```text
tpfireman GET https://jsonplaceholder.typicode.com/posts/1
```

**POST request with interactive payload:**
```text
tpfireman POST https://jsonplaceholder.typicode.com/posts
```
- The script will ask if you want to provide a JSON payload.
- Type y to enter the JSON string.

**PUT request with interactive payload:**
```text
tpfireman PUT https://jsonplaceholder.typicode.com/posts/1
```

**Exporting a response:**
```text
tpfireman GET https://jsonplaceholder.typicode.com/posts/1 EXPORT:TRUE
```
- The client asks for an export path; press Enter to use `api_response.txt` in the current directory. If the target already exists, it asks before overwriting it.

## Integration Tests

The integration tests send live requests to JSONPlaceholder and require an internet connection:

```powershell
python -m unittest discover -s tests -v
```

JSONPlaceholder simulates write operations; changes made by `POST`, `PUT`, `PATCH`, and `DELETE` are not persisted. The tests cover `GET`, `POST`, `PUT`, `PATCH`, and `DELETE`.

## Error Handling
- If an invalid JSON is provided during interactive input, the script will notify you and exit.
- HTTP responses, including errors, display status code, headers, and body. HTTP error responses exit with a non-zero code.
- Request timeout defaults to 10 seconds; set it with `--timeout SECONDS`, for example `tpfireman GET https://example.com --timeout 30`.
- The script will warn you if it's being run as Administrator, as it's designed for standard user sessions.

## Installation and wrapper checks

The installer rejects elevated sessions, checks for the launcher and application modules plus Python 3.8+, copies the app into the current user's Local AppData, prepares its user-data folder, and updates only the current user's PATH. GitHub Releases must use a SemVer tag such as `v1.2.3` and include `tpfireman-source.zip` with `main.py`, `auth_store.py`, `VERSION`, `README.md`, `uninstall.ps1`, `update.ps1`, and `bin/tpfireman.bat` at the archive root (or one directory below it). To run the installation and wrapper verification tests:

```powershell
python -m unittest tests.test_installation -v
```

The Windows-only wrapper smoke test and token elevation check are skipped on non-Windows systems. To verify the non-administrator scenario, run the tests from a standard (non-elevated) Windows terminal.
