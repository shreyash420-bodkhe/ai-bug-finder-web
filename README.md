# AI Bug Finder

AI Bug Finder is a Streamlit workbench for finding common Python defects. It combines syntax parsing, AST-based undefined-name checks, security and logic analysis, an optional timeout-limited runtime smoke test, a JSON bug catalog, conservative fix generation, and downloadable reports.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the URL printed by Streamlit, choose a bundled example or upload a `.py` file, review the Python error reference in the sidebar, and select **Analyze code**. Runtime smoke tests execute submitted code in a short-lived subprocess, so only run code you trust.

## Run offline

The Streamlit app and its built-in analysis run on your computer; it does not need GitHub or a hosted service. Install the requirements while internet access is available, then start the app in offline mode:

```powershell
$env:BUGFINDER_OFFLINE = "true"
.\.venv\Scripts\Activate.ps1
streamlit run app.py --server.address 127.0.0.1
```

Open the local URL printed by Streamlit (normally `http://127.0.0.1:8501`). Offline mode disables AI-provider requests even if an API key is configured. The interface uses system fonts and does not fetch web fonts. Analysis history and accounts are stored locally. To install on a computer that has never had internet access, download the required Python packages on a compatible internet-connected computer and transfer them along with the project before installing.

## Windows desktop app

The project also includes a native Windows desktop app that reuses the same analysis engine. It does not start a local web server or open a browser. The desktop version supports pasting code or opening a single `.py` file, reviewing findings and conservative fix previews, and exporting reports.

In PowerShell, install the desktop dependencies and start the window:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-desktop.txt
python desktop_app.py
```

The desktop app supports user registration and sign-in, plus a per-user analysis history. The sign-in screen has separate **Sign in** and **Admin login** tabs. Admins use the configured administrator credentials; admin accounts cannot be registered from the app. The local-development defaults and environment-variable overrides are described in the authentication section below. Admins can view registered account emails and saved analysis history, and set a new password for a selected user. Existing passwords are never displayed or stored in plaintext; new passwords are salted and hashed. When running from source, the desktop app shares the existing local databases; the packaged executable keeps persistent databases under `%LOCALAPPDATA%\AI Bug Finder`. The conservative fix preview can now detect and suggest fixes for direct string-plus-number literal expressions without running submitted code; ambiguous findings still require manual review.

To package a standalone Windows executable, install `requirements-desktop.txt`, then run this from the project folder:

```powershell
python -m pip install -r requirements-desktop.txt
python -m PyInstaller --noconfirm --clean AI-Bug-Finder.spec
```

The executable is written to `dist\AI-Bug-Finder.exe`; copy that file to a Windows computer to run the app without installing Python. The app stores account and history databases under `%LOCALAPPDATA%\AI Bug Finder`. Runtime smoke tests are unavailable in the packaged app; in the source version they are off by default and should only be enabled for code you trust. The existing Streamlit app remains available through `streamlit run app.py`.

## Android app

An Android companion app is provided in `mobile_app.py`. It reuses the analyzer and account code, with user registration/sign-in, a separate admin login, per-device analysis history, fix previews, and an admin user list/password-reset screen. Runtime smoke tests are disabled on mobile. Android accounts and history are stored privately on that device and do not automatically sync with the Windows app.

Build an APK from Linux or WSL (Buildozer does not build Android packages directly on Windows). Keep the project inside the Linux filesystem when using WSL for better build performance:

```bash
cd /path/to/shreyasaibugfinder
python3 -m venv .venv-mobile
source .venv-mobile/bin/activate
python -m pip install --upgrade pip buildozer
buildozer android debug
```

The APK is created under `bin/`. Copy it to the Android device and install it, allowing installation from that source when Android asks. Configure the administrator credentials before using the admin login. See `buildozer.spec` for package/build settings.

With authentication enabled, users must register with an email address and a password of at least 8 characters before signing in. Passwords are stored as salted hashes. There is no default administrator login: admin sign-in is disabled until both `BUGFINDER_ADMIN_EMAIL` and `BUGFINDER_ADMIN_PASSWORD` are configured. For local PowerShell use, set them before starting the app:

```powershell
$env:BUGFINDER_ADMIN_EMAIL = "admin@example.com"
$env:BUGFINDER_ADMIN_PASSWORD = "choose-a-strong-password"
```

For Streamlit Community Cloud, add both values in the app's **Settings → Secrets**. The login screen provides a separate **Admin login** tab. The admin view lists registered emails and analysis history, but never displays user passwords. Use an OIDC identity provider for production deployments.

### Persistent PostgreSQL storage

By default, local development uses SQLite files. Hosted instances should use a managed PostgreSQL database for persistent account and analysis history. Provision a PostgreSQL database (for example, on Neon or Supabase) and add its private connection string to Streamlit Community Cloud under **Manage app → Settings → Secrets**:

```toml
DATABASE_URL = "postgresql://user:password@host:5432/database?sslmode=require"
BUGFINDER_ADMIN_EMAIL = "admin@example.com"
BUGFINDER_ADMIN_PASSWORD = "use-a-long-unique-password"
```

The app creates its `users` and `analyses` tables automatically. Never commit the connection string or admin password. Analysis history includes submitted source code; restrict database access and tell users before collecting or storing their code.

For broader review of pasted code, set `OPENAI_API_KEY` in the environment or Streamlit secrets and enable **Request a full-code AI review**. Pasted source is sent to the configured AI provider only when you opt in. Without a key or opt-in, the app uses its local analyzers and supported fix patterns. AI-proposed corrections are syntax-checked and shown for review; they are never applied automatically. Accounts and analysis history both use the same SQLite database locally or PostgreSQL database when `DATABASE_URL` is configured.

```toml
# .streamlit/secrets.toml (do not commit this file)
OPENAI_API_KEY = "your-api-key"
```

## Project layout

- `app.py`: Streamlit frontend
- `analyzer/`: syntax, AST, runtime, and security analysis
- `database/`: Python built-in exception and warning catalog, security/logic patterns, solutions, and lookup helper
- `engine/`: detection pipeline, matching, similarity, solutions, and conservative fixes
- `reports/`: JSON, Markdown, and PDF report builders
- `tests/`: pytest coverage for analyzers, database, and engine
- `test_cases/`: example inputs for syntax, name, type, security, timeout, and logic defects

## Quick CLI check

```powershell
python -c "from engine import detect_bugs; print(detect_bugs('print(missing_name)', run_code=False))"
```

Run the automated tests with:

```powershell
python -m pytest -q
```

## Deployment controls

The project includes a `Dockerfile` and secure Streamlit defaults. For production deployments:

```powershell
$env:BUGFINDER_AUTH_ENABLED = "true"
$env:BUGFINDER_RUNTIME_SANDBOX = "docker"
$env:DATABASE_URL = "postgresql://user:password@host:5432/bugfinder"
docker build -t ai-bug-finder .
docker run --rm -p 8501:8501 ai-bug-finder
```

Configure Streamlit OIDC secrets before enabling authentication. Read [SECURITY.md](SECURITY.md) before accepting untrusted code or deploying with multiple users.
