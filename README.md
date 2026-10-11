<div align="center">

# 🔥 tpfireman

### Your no-frills HTTP client for the terminal.

Send API requests, manage authentication, and inspect responses directly from Windows.

[![Windows](https://img.shields.io/badge/Windows-10%2B-0078D4?logo=windows&logoColor=white)](#installation)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](#installation)
[![No dependencies](https://img.shields.io/badge/dependencies-none-2ea44f)](#)
[![License](https://img.shields.io/badge/license-MIT-8b5cf6)](LICENSE)

</div>

---

## ⚡ At a glance

`tpfireman` is a lightweight, interactive command-line client for testing HTTP APIs. It uses Python's standard library, so there are no third-party packages to install.

| Method | Purpose |
|:--|:--|
| `GET` | Read data |
| `POST` | Create resources |
| `PUT` | Replace resources |
| `PATCH` | Modify resources |
| `DELETE` | Remove resources |

## ✨ Features

| | Feature |
|:--|:--|
| 🚀 | `GET`, `POST`, `PUT`, `PATCH`, and `DELETE` requests |
| 🧩 | Interactive JSON payload input and automatic `Content-Type` handling |
| 🎨 | Pretty-printed JSON responses and colorized terminal output (automatically disabled for redirected output or `NO_COLOR`) |
| 📦 | Export responses to a file, with confirmation before overwriting |
| 🔐 | Custom headers and reusable authentication profiles |
| 🛡️ | Secrets encrypted with Windows DPAPI; sensitive values are never displayed |
| 🔑 | Bearer, Basic, API key, and OAuth2 (Client Credentials / Authorization Code with PKCE) |
| ⏱️ | Configurable timeouts and consistent display of HTTP error responses |
| 🔔 | Best-effort startup check for newer GitHub releases, with an update command suggestion |
| 🗂️ | Reusable request history with labels, editing, and deletion |

## 📥 Installation

### Requirements

- Windows and Python **3.8 or newer**, available as `python` on `PATH`.
- A **non-elevated** PowerShell session.

### Install

Open PowerShell in the application files directory and run:

```powershell
.\install.ps1
```

The installer copies the app and its terminal UI module to `%LOCALAPPDATA%\Programs\tpfireman`, prepares `%LOCALAPPDATA%\tpfireman` for user data, and adds the command to your user `PATH`. No administrator privileges or additional Python dependencies are required. Restart your terminal when installation is complete.

## 🚦 Quick start

### Interactive session

Start a persistent session, then enter requests at the prompt:

```text
tpfireman
GET https://jsonplaceholder.typicode.com/posts/1
POST https://jsonplaceholder.typicode.com/posts
guided
```

Use `guided` for step-by-step prompts. Type `exit` or `quit` at any interactive prompt to close the session; the complete input must be the command (case and surrounding spaces are ignored).

### Direct requests

```powershell
# GET request
tpfireman GET https://jsonplaceholder.typicode.com/posts/1

# POST request; payload is entered interactively
tpfireman POST https://jsonplaceholder.typicode.com/posts

# Override the saved timeout for one request
tpfireman GET https://example.com --timeout 30

# Manage the saved default (300 seconds / 5 minutes)
tpfireman timeout show
tpfireman timeout edit 600
tpfireman timeout delete

# Omit seconds to enter the new value interactively
tpfireman timeout edit

# Export the response (you will be prompted for a file path)
tpfireman GET https://jsonplaceholder.typicode.com/posts/1 EXPORT:TRUE
```

> [!TIP]
> For `POST`, `PUT`, and `PATCH`, JSON payloads can be pasted across multiple lines; finish with an empty line. Custom header values are entered without being displayed.

### Request syntax

```text
tpfireman <METHOD> <URL> [--auth NAME_OR_ID] [--payload JSON] [--export TRUE|FALSE] [--timeout SECONDS]
```

Example with a saved authentication profile:

```powershell
tpfireman GET --auth my-api https://api.example.com --export false
tpfireman POST --auth my-api https://api.example.com/items --payload '{"name":"demo"}' --export true
```

## 🗂️ Request history

The default request timeout is 300 seconds (5 minutes), saved alongside authentication profiles and request history. Manage it with `tpfireman timeout show`, `tpfireman timeout edit [SECONDS]`, or `tpfireman timeout delete` (asks for confirmation and restores the 5-minute default). A per-request `--timeout SECONDS` overrides the saved value.

Successful requests are saved locally with their method, URL, optional payload, export setting, and label. Entries are deduplicated by method and URL and updated when reused.

- New entries use the URL as their default label; redundant labels are hidden in the list.
- Select entries by ID, label, or URL.
- In the label prompt, enter `=` to reset the label to the current URL.
- In the payload prompt, enter `-` to clear the payload; press Enter to keep any current value.
- Multiline JSON payload input ends with an empty line.

| Command | Action |
|:--|:--|
| `tpfireman history` | List saved requests and show available commands |
| `tpfireman history <id\|label\|url>` | Review and run a saved request |
| `tpfireman history edit <id\|label\|url>` | Edit a request without running it |
| `tpfireman history delete <id\|label> [<id\|label> ...]` | Delete one or more requests (confirmation required) |

Changes made while reviewing a request are saved automatically. History is stored in `%LOCALAPPDATA%\tpfireman\request_history.json`.

## 🔐 Authentication profiles

Manage reusable profiles without exposing secret values:

| Command | Action |
|:--|:--|
| `tpfireman auth` | List saved profiles and show available commands |
| `tpfireman auth add` | Create a profile |
| `tpfireman auth edit <name-or-id>` | Edit a profile |
| `tpfireman auth rename <name-or-id> <new-name>` | Rename a profile |
| `tpfireman auth delete <name-or-id> [name-or-id ...]` | Delete selected profiles (confirmation required) |
| `tpfireman auth delete --all` | Delete all profiles (confirmation required) |

`tpfireman auth list` is an alias for `tpfireman auth`. Profiles are stored in `%LOCALAPPDATA%\tpfireman\auth_profiles.json`; secrets are protected with Windows DPAPI.

## 📤 Responses and exports

The client displays the status code, headers, and response body, including for HTTP errors. JSON bodies are formatted for readability; non-JSON text remains readable as-is.

Use `EXPORT:TRUE` (or `--export true`) to save a response. tpfireman prompts for a file path; press Enter to use `api_response.txt` in the current directory. Existing files are never overwritten without confirmation.

## 🔄 Version, updates, and uninstall

```text
tpfireman version
tpfireman update
tpfireman uninstall
```

At startup, tpfireman checks GitHub Releases on a best-effort basis and suggests `tpfireman update` when a newer version is available. Network or API failures do not prevent startup; the check does not install anything automatically.

Run `tpfireman update` to check and install an update. If a required application module such as `history_store.py` or `terminal_ui.py` is missing, the updater offers to reinstall the latest release even when the version number is current. Confirmation accepts `YES`, `yes`, `Y`, or `y`; user data is preserved.

> [!WARNING]
> Uninstallation requires confirmation and removes the application, its exact `PATH` entry, and all tpfireman user data, including authentication profiles. **This cannot be undone.**

> [!NOTE]
> To publish a release, use a SemVer tag (for example, `v1.2.3`) and attach `tpfireman-source.zip` containing the application files and a matching `VERSION` file.

## 🧪 Tests

Run local installation, wrapper, authentication, export, and response checks with:

```powershell
python -m unittest tests.test_installation -v
python -m unittest tests.test_auth_store tests.test_export tests.test_http_response -v
```

Integration tests send live requests to JSONPlaceholder and require an internet connection:

```powershell
python -m unittest discover -s tests -v
```

JSONPlaceholder simulates write operations; changes sent with `POST`, `PUT`, `PATCH`, and `DELETE` are not persisted. The Windows token check and wrapper smoke test are only available on Windows. To verify the standard-user scenario, run tests from a non-elevated session.

---

<div align="center">

**🔥 Small client. Your requests, under control.**

</div>
