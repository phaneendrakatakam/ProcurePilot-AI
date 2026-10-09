# ProcurePilot

**An end-to-end, role-based procurement and accounts-payable workflow platform.**

ProcurePilot models the operational journey from an employee's purchase request through sourcing, multi-level approval, purchase order issuance, goods receipt, invoice verification, and payment finalization. Built as a portfolio engineering project, it emphasizes **workflow correctness, authorization, financial controls, and auditability** over AI-generated decisions.


## The problem

A purchase is rarely a single approval. In an organization, employees, procurement, suppliers, receiving teams, and finance each own different steps and controls. When those steps are scattered across spreadsheets, email, and disconnected systems, it becomes harder to establish who approved a purchase, which supplier quotation was selected, whether goods arrived, and whether an invoice should be paid.

**ProcurePilot brings that lifecycle into one controlled workflow** with explicit ownership, permissions, state changes, and audit records.

## Procurement lifecycle

```text
Employee purchase request
          |
          v
Procurement sourcing & RFQ
          |
          v
Supplier quotations & selection
          |
          v
Manager -> Procurement Head -> Finance approvals
          |
          v
Purchase order creation & issuance
          |
          v
Goods receipt
          |
          v
Supplier invoice validation
          |
          v
Three-way matching (PO / receipt / invoice)
          |
          v
Finance payment finalization -> PAID
```

A typical transaction follows these steps:

1. **Request:** An employee creates a purchase request with business requirements.
2. **Source:** Procurement prepares an RFQ, contacts suppliers, and captures quotations.
3. **Select:** Supplier responses are compared and a supplier is selected.
4. **Approve:** Authorized managers review the request through the configured approval sequence.
5. **Order:** A purchase order is created and formally issued to the selected supplier.
6. **Receive:** The receiving team records accepted goods or delivery.
7. **Invoice:** Accounts payable captures and validates the supplier's invoice.
8. **Match and pay:** The system checks purchase order, receipt, and invoice consistency; finance can finalize payment only after the required checks succeed.

## Key capabilities

| Area | What ProcurePilot supports |
| --- | --- |
| Purchase requests | Request creation, procurement review, and lifecycle tracking |
| Sourcing | RFQs, supplier responses, quotation comparison, and supplier selection |
| Purchasing | Multi-level approvals, purchase order creation, and supplier notification |
| Receiving | Goods receipt recording against procurement records |
| Accounts payable | Supplier invoices, validation, and three-way matching |
| Payments | Controlled finance finalization with payment reference, time, and actor |
| Governance | Database-backed role-based access control, audit events, and administrative master data |
| Operations | Role-aware workspaces, dashboards, and notification automation |

### Built-in controls

- **Role-based access control (RBAC):** Access is checked against persisted roles and permissions, rather than relying only on UI visibility.
- **Separation of responsibilities:** Employees, sourcing, approvals, receiving, accounts payable, and finance have distinct responsibilities.
- **Approval controls:** The workflow records decisions and routes work through the appropriate decision makers.
- **Three-way matching:** Payment cannot be finalized until the invoice has a successful match against the order and recorded receipt.
- **Payment traceability:** The payment reference, timestamp, and user responsible for finalization are stored.
- **Auditability:** Business and system actions are recorded for later review.

## Roles

| Role | Primary responsibility |
| --- | --- |
| Employee | Create and follow purchase requests |
| Manager | Review department purchase requests |
| Procurement Analyst | Source suppliers and manage RFQs/quotations |
| Procurement Head | Oversee procurement decisions and issue purchase orders |
| Goods Receiver | Record goods receipts |
| AP Analyst | Validate invoices and resolve invoice-related issues |
| Finance Manager | Review finance decisions and finalize cleared payments |
| Administrator | Manage users, access, master data, and audit visibility |

Permissions are enforced by the backend. A user cannot perform a restricted finance action simply by navigating to another page or calling an endpoint directly.

## Technology

| Layer | Technology |
| --- | --- |
| API/backend | Python, FastAPI |
| Data access | SQLAlchemy 2 |
| Database | PostgreSQL, Psycopg 3 |
| Schema evolution | Alembic |
| Validation and settings | Pydantic, pydantic-settings |
| Authentication | JWT-based authentication and Argon2 password hashing |
| Frontend | HTML, CSS, and JavaScript served by FastAPI |
| Testing | Pytest and HTTPX |

### Repository structure

```text
app/
  api/         HTTP endpoints, routing, and authorization dependencies
  core/        Configuration, database, and security utilities
  models/      Database models
  schemas/     Request and response validation
  services/    Domain services and workflow logic
  seed/        Development bootstrap and sample users
  web/         Login, application UI, and static assets
alembic/       Versioned database migrations
scripts/       Verification and operational utilities
tests/         Automated tests
```

## Run locally

### Prerequisites

- Python 3.11+ (recommended)
- PostgreSQL running locally or reachable through a valid connection URL
- Git

> **Configuration note:** `.env` and `.env.example` are intentionally **not included in this public repository**. Create your own `.env` file locally. Never commit credentials. The values below are illustrative only.

### 1. Clone and install

```powershell
git clone https://github.com/phaneendrakatakam/ProcurePilot-AI.git
cd ProcurePilot-AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. Configure the environment

Create a local `.env` file in the project root containing at least:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+psycopg://YOUR_DB_USER:YOUR_DB_PASSWORD@localhost:5432/procurepilot_ai
SECRET_KEY=REPLACE_WITH_A_LONG_RANDOM_SECRET
PUBLIC_BASE_URL=http://localhost:8000
```

Create the matching PostgreSQL database before applying migrations. For a PostgreSQL URL, percent-encode reserved characters in usernames/passwords. Other optional settings, including SMTP and automation controls, are defined in `app/core/config.py`.

**Security:** The application contains development-only fallback configuration; set your own strong `SECRET_KEY` and database credentials before using it outside an isolated local environment. Do not use these example values in production.

### 3. Initialize the database and sample data

```powershell
python -m alembic upgrade head
python -m app.seed.bootstrap
```

To create local role-specific demonstration users, optionally run:

```powershell
python -m app.seed.create_role_demo_users
```

That command asks you to enter a temporary password interactively. It does not require a published shared password.

### 4. Start the application

```powershell
python -m uvicorn app.main:app --reload
```

Open:

- **Login:** http://localhost:8000/login
- **API documentation:** http://localhost:8000/docs

An administrator account can be created through the development administration bootstrap in `app/seed/create_admin.py`; inspect that script's instructions before use.

### 5. Run tests

```powershell
$env:PYTHONUTF8 = "1"
python -m pytest -q
```

The initial release completed with **129 tests passing** on Windows. Test coverage includes authorization, approval routing, sourcing, purchase orders, goods receipt, invoices, matching, payment finalization, and UI/API behavior. Passing automated tests do not imply that every production deployment configuration has been validated.

An additional local release audit script is available:

```powershell
.\Invoke-ProcurePilot-ReleaseAudit.ps1
```

## Design approach

**Deterministic workflows instead of AI approvals.** ProcurePilot is intentionally a controlled business application, not an autonomous purchasing agent. Authorization, approval routing, accounting checks, and payment readiness should be understandable, repeatable, and auditable.

**Backend-enforced policy.** The UI provides role-aware workspaces, while the API remains responsible for permission checks and protected state transitions.

**An auditable chain of records.** Requests, supplier responses, purchase orders, receipts, invoices, and payments are represented as related business records rather than disconnected form submissions.

**Incremental database evolution.** Alembic migrations document schema changes as new parts of the procurement lifecycle are introduced.

## Validation scenario

The local end-to-end validation exercised a fictional office Wi-Fi upgrade purchase, including requests for networking hardware, supplier quotations, multiple approval roles, purchase order issuance, goods receipt, invoice matching, and completed payment. The exercise also surfaced edge cases that informed follow-up fixes and tests.

This is a **fictional demonstration scenario**, not a claim of live enterprise adoption or real payments.

## Scope and limitations

- ProcurePilot is a **portfolio project**, not a certified ERP or production financial system.
- Supplier emails require configured SMTP settings; local setup alone does not guarantee email delivery.
- The public repository does not include secrets, local databases, or demonstration screenshots.
- No hosted public instance or deployment availability is claimed here.
- Real-world use would require additional operational review, security assessment, monitoring, backups, and organization-specific policy configuration.

## Author

**Phaneendra Katakam**  
[GitHub](https://github.com/phaneendrakatakam) · [Portfolio](https://phaneendrakatakam.github.io/)

---

*ProcurePilot demonstrates the engineering of reliable, human-governed procurement workflows from request to payment.*
