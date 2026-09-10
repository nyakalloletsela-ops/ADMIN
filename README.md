# ADMIN — Farm & Property Management

ADMIN is the operational system of record for farm and property coordination. It turns the Administrative Officer workplan into a working web application with task coordination, recurring schedules, operational records, reminders, audit history and configurable integrations.

## Current status

**Working production foundation / MVP.** The application is executable today and is being expanded as tested vertical slices. The old feasibility spike has been replaced by the application under `app/`.

ADMIN is the system of record. External providers are optional adapters and are never authoritative for ADMIN business state.

## Run locally

Python 3.11+ is recommended. No third-party package is required for the local baseline.

```powershell
$env:ADMIN_PASSWORD="change-this-before-use"
python app/server.py
```

Open `http://localhost:8000` and sign in with username `admin` and the configured password.

For a real deployment, set a strong password through the deployment secret manager and use HTTPS. Never commit credentials, provider tokens or API keys.

## Implemented foundation

- authenticated admin session
- password hashing and signed session cookie
- SQLite WAL database for the runnable baseline
- users, roles and permission records
- task register and intention-revealing task transitions
- recurring task templates and deterministic occurrence generation
- due/overdue reminder generation
- tenants, properties/units, invoices/payments, maintenance, stock, assets and incidents
- append-only payment records
- stock movement ledger instead of silent quantity edits
- immutable audit entries for important mutations
- configurable integration registry with secrets excluded from normal reads
- health endpoint and responsive mobile-friendly dashboard
- JSON API under `/api/v1`

## Architecture

The application is a modular monolith. PostgreSQL is the target production database; SQLite keeps the repository runnable without external dependencies. Database access is isolated so a PostgreSQL adapter can replace SQLite without moving business rules into the UI.

External APIs are configured by an authorised administrator. Provider SDKs and credentials must not be hard-coded into business modules. Unconfigured integrations remain `INACTIVE` and cannot claim successful delivery.

See `docs/PRODUCTION_IMPLEMENTATION.md`, `docs/data-model.md`, `docs/workflows.md`, `docs/api-contract.md`, and `docs/testing-strategy.md` for the governing design.

## Source requirements

The two source PDFs remain in the repository. `docs/activity-inventory.md` is the traceability matrix from those documents to automation behaviour.
