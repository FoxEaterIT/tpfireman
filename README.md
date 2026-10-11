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

```text
GET  → read data         POST   → create resources
PUT  → replace           PATCH  → modify
DELETE → remove
```

## ✨ Features

| | Feature |
|:--|:--|
| 🚀 | `GET`, `POST`, `PUT`, `PATCH`, and `DELETE` requests |
| 🧩 | Interactive JSON payload input and automatic `Content-Type` handling |
| 🎨 | Pretty-printed JSON responses and colorized terminal output |
| 📦 | Export responses to a file, with confirmation before overwriting |
| 🔐 | Custom headers and reusable authentication profiles |
| 🛡️ | Secrets encrypted with Windows DPAPI; sensitive values are never displayed |
| 🔑 | Bearer, Basic, API key, and OAuth2 (Client Credentials / Authorization Code with PKCE) |
| ⏱️ | Configurable timeouts and consistent display of HTTP error responses |
| 🔔 | Best-effort startup check for newer GitHub releases, with an update command suggestion |

## 📥 Installation

### Requirements

- Windows and Python **3.8 or newer**, available as `python` on `PATH`.
- A **non-elevated** PowerShell session.

### Install

Open PowerShell in the application files directory and run:

```powershell
.\install.ps1
```

The installer copies the app to `%LOCALAPPDATA%\Programs\tpfireman`, prepares `%LOCALAPPDATA%\tpfireman` for user data, and adds the command to your user `PATH`. No administrator privileges or additional Python dependencies are required. Restart your terminal when installation is complete.

## 🚦 Quick start

```powershell
# Start an interactive session (type exit to leave)
tpfireman

# Send a request directly at the session prompt
GET https://jsonplaceholder.typicode.com/posts/1

# Or choose guided prompts from the session prompt
guided

# Send a GET request
tpfireman GET https://jsonplaceholder.typicode.com/posts/1

# Send a POST request; the client will ask whether you want to enter a JSON payload
tpfireman POST https://jsonplaceholder.typicode.com/posts

# Set a 30-second timeout
tpfireman GET https://example.com --timeout 30

# Export the response (you will be prompted for a file path)
tpfireman GET https://jsonplaceholder.typicode.com/posts/1 EXPORT:TRUE
```

> [!TIP]
> For `POST`, `PUT`, and `PATCH`, you can enter JSON interactively. Payloads are not accepted as command-line arguments. You can also add custom headers interactively; their values are entered without being displayed.

### Syntax

```text
tpfireman <METHOD> <URL> [--timeout SECONDS] [EXPORT:TRUE|FALSE]
```

### Authentication profiles

Manage reusable profiles without exposing secrets in the terminal:

```text
tpfireman auth add
tpfireman auth list
tpfireman auth edit
tpfireman auth rename
tpfireman auth delete
```

Delete all profiles with `tpfireman auth delete --all` (confirmation required). Profile data is stored in `%LOCALAPPDATA%\tpfireman\auth_profiles.json`; secrets are protected with Windows DPAPI.

## 📤 Responses and exports

The client displays the status code, headers, and response body, including for HTTP errors. JSON bodies are formatted for readability; non-JSON text remains readable as-is. Use `EXPORT:TRUE` to choose where to save a response. If the file already exists, tpfireman asks before overwriting it. Press Enter to use `api_response.txt` in the current directory.

## 🔄 Version, updates, and uninstall

```text
tpfireman version
tpfireman update
tpfireman uninstall
```

On startup, tpfireman makes a best-effort check of [FoxEaterIT/tpfireman GitHub Releases](https://github.com/FoxEaterIT/tpfireman). If a newer version is available, it suggests running `tpfireman update`; network or API failures do not prevent the client from starting. The check uses a short timeout and does not download or install anything automatically. Run `tpfireman update` to check and install an update; the updater asks for confirmation (accepted responses: `YES`, `yes`, `Y`, or `y`) and preserves user data. Uninstallation requires confirmation and removes the application, its exact `PATH` entry, and all user data, including authentication profiles. **Removing user data cannot be undone.**

> [!NOTE]
> To publish a release, use a SemVer tag (for example, `v1.2.3`) and attach `tpfireman-source.zip` containing the application files and a matching `VERSION` file.

## 🧪 Tests

Run the installation, wrapper, and authentication checks with:

```powershell
python -m unittest tests.test_installation -v
python -m unittest tests.test_auth_store tests.test_export tests.test_http_response -v
```

Integration tests send live requests to JSONPlaceholder and require an internet connection:

```powershell
python -m unittest discover -s tests -v
```

JSONPlaceholder simulates write operations; changes sent with `POST`, `PUT`, `PATCH`, and `DELETE` are not persisted. The Windows token check and wrapper smoke test are only available on Windows. To verify the standard-user scenario, run the tests from a non-elevated session.

---

<div align="center">

**🔥 Small client. Your requests, under control.**

</div>
