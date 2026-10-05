# Security and deployment

## Runtime sandbox

Runtime checks are opt-in. For stronger isolation, run the app where Docker is available and set:

```powershell
$env:BUGFINDER_RUNTIME_SANDBOX = "docker"
```

The Docker runner uses no network, a read-only filesystem, a temporary `/tmp`, CPU and memory limits, and a process limit. Keep the app behind authentication and a reverse proxy in production. Container isolation is a deployment control, not a guarantee against every kernel or Docker configuration failure.

## Authentication

Enable Streamlit OIDC authentication with `BUGFINDER_AUTH_ENABLED=true` and configure the `oidc` section in `.streamlit/secrets.toml`. Never commit secrets. The app remains usable without authentication for local development.

## Data storage

SQLite is the default local history database. For multiple deployed workers, set `DATABASE_URL` to a PostgreSQL connection string and install the requirements. Use encrypted connections and database access controls in production.

## AI privacy

Use Local-only mode when source code must not leave the machine. If a cloud API key is configured, selected source code and the last five history contexts may be sent to the configured AI endpoint. API keys are read from the session or environment and are not written to history.
