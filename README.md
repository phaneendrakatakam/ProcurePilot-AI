
# ProcurePilot

### End-to-End Procurement & Accounts Payable Management Platform

ProcurePilot is a full-stack, role-based procurement management platform designed to model the complete enterprise purchasing lifecycle — from purchase requisition and supplier sourcing to purchase order issuance, goods receipt, invoice matching, and payment finalization.

Built with **Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, and JavaScript**, ProcurePilot focuses on workflow governance, role-based authorization, financial controls, and auditable business operations.

**Release:** v1.0.0 — Initial Portfolio Release  
**Status:** Portfolio project | Local execution  
**Architecture:** Modular monolith  
**AI integration:** Not included in the current release

---

## Overview

Enterprise procurement involves multiple departments, approval levels, supplier interactions, and financial checkpoints.

When these activities are handled through disconnected emails, spreadsheets, and manual processes, organizations can experience:

- Limited visibility into purchasing requests
- Delayed approvals and unclear ownership
- Inconsistent supplier quotation comparisons
- Purchase orders without adequate authorization
- Weak coordination between receiving and finance
- Invoice discrepancies and payment-control risks
- Difficulties tracking decisions and responsibilities

**ProcurePilot brings these activities into one structured application with defined responsibilities and controlled state transitions.**

The platform demonstrates how an enterprise workflow can coordinate employees, procurement professionals, suppliers, receiving teams, and finance personnel while maintaining accountability across the purchasing process.

---

## Key Capabilities

### Purchase Requisition Management

- Create and track purchase requests
- Capture purchasing requirements and estimates
- Apply required-information, budget, and policy checks
- Track procurement progress through lifecycle stages
- Maintain traceability between requests and downstream procurement records

### Supplier Sourcing & RFQs

- Initiate sourcing against purchase requests
- Manage supplier information
- Create requests for quotation (RFQs)
- Send RFQ notifications through configured email services
- Capture supplier quotation responses
- Support itemized supplier quotations
- Compare offers and select a supplier

### Multi-Level Approvals

- Route purchasing decisions through assigned roles
- Support manager approval
- Support procurement leadership approval
- Support finance approval
- Enforce permission-based access to approval actions
- Record approval decisions for auditability

### Purchase Order Management

- Generate purchase orders from approved procurement decisions
- Support itemized purchase order details
- Maintain supplier and purchasing information
- Separate purchase order creation from authorized issuance
- Track supplier notification activity

### Goods Receipt Management

- Record received goods against purchase orders
- Maintain a receipt record for downstream financial controls
- Provide receiving information for invoice reconciliation

### Accounts Payable & Three-Way Matching

- Capture supplier invoices
- Validate invoice information
- Compare purchase order, goods receipt, and invoice data
- Identify matching exceptions
- Restrict payment finalization until required checks succeed
- Record payment reference, timestamp, and responsible user

### Administration & Auditability

- Database-backed user roles and permissions
- Administrative access to platform management functions
- Human and system audit events
- Traceable procurement and financial decisions
- Workflow notification and reminder automation

---

## End-to-End Procurement Lifecycle

ProcurePilot follows a defined purchasing and accounts-payable workflow.

```mermaid
flowchart TD
    A["Purchase Requisition"] --> B["Requirement, Budget & Policy Checks"]
    B --> C["Supplier Sourcing"]
    C --> D["RFQ Distribution"]
    D --> E["Quotation Collection & Comparison"]
    E --> F["Supplier Selection"]
    F --> G["Manager Approval"]
    G --> H["Procurement Head Approval"]
    H --> I["Finance Approval"]
    I --> J["Purchase Order Creation"]
    J --> K["Authorized PO Issuance"]
    K --> L["Goods Receipt"]
    L --> M["Supplier Invoice Validation"]
    M --> N{"Three-Way Match"}
    N -->|"Matched"| O["Finance Review"]
    N -->|"Exception"| P["Blocked / Requires Resolution"]
    O --> Q["Payment Finalization"]
    Q --> R["Paid & Audited"]
```

The workflow illustrates the intended progression from procurement initiation to payment completion.

Some actions require a specific role, and some transitions depend on prior approvals or successful validation.

---

## Roles & Responsibilities

ProcurePilot separates responsibilities across the organization rather than giving every user access to every operation.

| Role | Primary Responsibility |
|---|---|
| Employee | Create and track purchase requisitions |
| Manager | Review assigned purchasing approvals |
| Procurement Analyst | Handle sourcing, RFQs, quotations, and procurement operations |
| Procurement Head | Review procurement approvals and authorize purchase order issuance |
| Finance Manager | Review financial approvals and finalize eligible payments |
| AP Analyst | Capture and validate supplier invoices |
| Goods Receiver | Record goods received against purchase orders |
| Administrator | Manage platform administration and authorized audit access |

Authorization is enforced on the backend using database-backed role and permission information.

The interface also presents role-relevant functionality, but interface visibility is not treated as a replacement for server-side authorization.

---

## System Architecture

ProcurePilot uses a **modular monolith** architecture.

The frontend, API routes, business services, and data access components are maintained within one application, with responsibilities separated into modules.

```mermaid
flowchart TB
    U["Users Across Procurement & Finance Roles"]

    subgraph FRONTEND["Presentation Layer"]
        UI["HTML / CSS / JavaScript"]
        LOGIN["Authentication & Role-Aware Workspaces"]
    end

    subgraph BACKEND["FastAPI Application"]
        API["REST API Routes"]
        AUTH["Authentication & RBAC"]
        SERVICES["Business Services & Workflow Rules"]
        AUDIT["Audit & Automation Services"]
        ORM["SQLAlchemy Models"]
    end

    subgraph DATA["Persistence Layer"]
        DB[("PostgreSQL")]
        MIG["Alembic Migrations"]
    end

    MAIL["Optional SMTP Email Service"]
    SUP["Suppliers / RFQ Recipients"]

    U --> UI
    UI --> LOGIN
    LOGIN --> API

    API --> AUTH
    API --> SERVICES
    SERVICES --> AUDIT
    SERVICES --> ORM
    AUTH --> ORM
    AUDIT --> ORM
    ORM <--> DB
    MIG --> DB

    SERVICES --> MAIL
    MAIL --> SUP
```

### Architecture Components

**Presentation layer**

The application serves a browser-based interface using HTML, CSS, and vanilla JavaScript.

It provides role-aware procurement workspaces and interacts with backend API endpoints.

**API layer**

FastAPI exposes REST endpoints for procurement operations, authentication, approvals, suppliers, purchase orders, goods receipts, invoices, and administrative capabilities.

**Business logic layer**

Service modules manage business rules and responsibilities such as approval routing, quotation processing, audit recording, notification automation, and supplier communication.

**Persistence layer**

SQLAlchemy provides database models and access patterns, while PostgreSQL stores transactional and governance information.

Alembic manages schema migrations.

**Integration layer**

SMTP configuration supports supplier email notifications. Email-related behavior depends on the environment and configured mail service.

### Architectural Approach

The modular monolith was chosen to keep the application understandable and manageable while maintaining boundaries between procurement domains.

It avoids unnecessary microservice infrastructure for a portfolio-scale application while allowing individual modules to evolve independently.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| API validation | Pydantic |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Database migrations | Alembic |
| Frontend | HTML, CSS, JavaScript |
| Authentication | JWT |
| Password hashing | Argon2 |
| Email | SMTP integration |
| Automated testing | Pytest, HTTPX |
| Version control | Git, GitHub |

---

## Project Structure

```text
ProcurePilot-AI/
│
├── app/
│   ├── api/
│   │   ├── dependencies/       # API authentication dependencies
│   │   ├── routes/             # Procurement and administrative endpoints
│   │   └── router.py
│   │
│   ├── core/                   # Configuration, database, security
│   ├── models/                 # SQLAlchemy database models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Workflow and domain services
│   ├── seed/                   # Database and demo-user setup
│   ├── web/
│   │   ├── static/
│   │   │   ├── css/
│   │   │   └── js/
│   │   ├── app.html
│   │   └── login.html
│   └── main.py                 # FastAPI entry point
│
├── alembic/
│   └── versions/               # Database migration history
│
├── scripts/                    # Verification and automation utilities
├── tests/                      # Automated tests
│
├── alembic.ini
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Security & Governance

ProcurePilot is designed around controlled business operations.

### Role-Based Access Control

Backend permission checks determine whether an authenticated user may perform sensitive actions.

### Authentication

JWT-based authentication and Argon2 password hashing support user identity management.

### Segregation of Duties

Procurement, receiving, administration, and financial operations are assigned to different responsibilities.

### Financial Controls

Invoice payment finalization is restricted to authorized finance operations.

A successful three-way match is required before payment can be finalized.

### Audit Trail

The system records operational events and relevant actors to improve traceability.

### Configuration Security

Environment-specific database credentials, JWT secrets, and SMTP credentials are expected to be configured locally.

Real credentials, local `.env` files, and private environment templates are not included in the published repository.

**Security note:** This is a portfolio release, not a security certification or production-hardening claim. Development defaults must be replaced before any non-development deployment.

---

## Local Development Setup

### Prerequisites

Install:

- Python 3.11 or newer
- PostgreSQL
- Git

Ensure PostgreSQL is running and that you have a database and database user available for ProcurePilot.

### 1. Clone the Repository

```bash
git clone https://github.com/phaneendrakatakam/ProcurePilot-AI.git
cd ProcurePilot-AI
```

### 2. Create a Python Virtual Environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure the Environment

Create a local `.env` file in the project root.

The repository intentionally does **not** publish `.env` or `.env.example`.

Example configuration using placeholders:

```dotenv
APP_ENV=development
APP_NAME=ProcurePilot
DATABASE_URL=postgresql+psycopg://YOUR_DB_USER:YOUR_DB_PASSWORD@localhost:5432/YOUR_DB_NAME
SECRET_KEY=REPLACE_WITH_A_LONG_RANDOM_SECRET
PUBLIC_BASE_URL=http://localhost:8000
```

Replace the placeholder values with your own local configuration.

If your PostgreSQL password contains URL-reserved characters, URL-encode those characters in `DATABASE_URL`.

Optional SMTP settings are available for supplier email notifications:

```dotenv
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=
SMTP_FROM_NAME=ProcurePilot
```

Configure these values only when using an appropriate mail service.

Never commit credentials or access tokens to GitHub.

### 5. Apply Database Migrations

```bash
python -m alembic upgrade head
```

This applies the versioned database schema changes.

### 6. Initialize Required Data

```bash
python -m app.seed.bootstrap
```

This initializes the application's foundational data.

### 7. Create Local Demo Users (Optional)

```bash
python -m app.seed.create_role_demo_users
```

The command prompts for a temporary demo password interactively.

It creates or refreshes fictional users representing the main procurement workflow roles.

These accounts are for local development and demonstrations only.

### 8. Start the Application

```bash
python -m uvicorn app.main:app --reload
```

Open:

- Application login: http://localhost:8000/login
- Application interface: http://localhost:8000/app
- API documentation: http://localhost:8000/docs

The root URL redirects to the login page.

---

## Testing & Validation

The project includes automated tests covering business logic, API behavior, role permissions, UI-related behavior, and financial workflow controls.

### Run the Test Suite

```bash
python -m pytest -q
```

For Windows environments where console encoding causes test issues:

```powershell
$env:PYTHONUTF8 = "1"
python -m pytest -q
```

### Validation Performed for v1.0.0

**129 automated tests passed** during the local release validation.

Additional validation included:

- Alembic migration checks
- Role-permission and approval behavior
- Purchase request workflow checks
- RFQ and supplier quotation processing
- Purchase order workflow checks
- Goods receipt behavior
- Invoice validation and three-way matching
- Payment finalization restrictions
- Historical end-to-end procurement data consistency

### End-to-End Scenario

A representative office network upgrade procurement was exercised through the workflow:

1. Employee purchase request
2. Supplier RFQ and quotation collection
3. Supplier selection
4. Manager, procurement, and finance approvals
5. Purchase order issuance
6. Goods receipt
7. Supplier invoice registration
8. Successful three-way match
9. Payment finalization and audit verification

This validation demonstrates the integration of procurement stages in a controlled local environment.

It should not be interpreted as a production performance benchmark or a guarantee that every possible operational scenario has been tested.

---

## Engineering Decisions

### Deterministic Workflows Instead of AI-Driven Decisions

ProcurePilot deliberately uses explicit business rules for approvals, permissions, and financial state transitions.

These decisions require predictability, accountability, and clear validation rather than probabilistic outputs.

Although the repository retains the historical `-AI` name, **this release does not include an AI model or LLM integration**.

### Stronger Financial Boundaries

Payment is not treated as a simple status update.

The workflow requires the appropriate authorization and successful matching conditions before payment finalization.

### Role-Aware User Experience

Different users interact with the same procurement lifecycle from different operational perspectives.

This helps demonstrate how shared enterprise records can support distinct responsibilities.

### Database Migrations

Versioned Alembic migrations enable schema evolution while maintaining a history of structural changes.

### Testable Business Rules

Automated tests exercise approval decisions, permission boundaries, procurement logic, and accounts-payable behaviors.

---

## Current Scope & Limitations

ProcurePilot v1.0.0 is a **source-code portfolio release**.

It demonstrates the design and implementation of a structured procurement platform, but it is not presented as a deployed commercial SaaS product.

Current scope considerations:

- A local PostgreSQL database is required.
- Email notifications depend on SMTP configuration.
- Demo accounts are intended for development and evaluation.
- The application has not been claimed as production-hardened.
- Payment finalization records an application-level payment outcome; it is not a banking or payment-gateway integration.
- The current release does not integrate an AI model.
- No hosted live demo is provided as part of this release.

---

## Potential Future Enhancements

Possible next steps include:

- Continuous integration with GitHub Actions
- Stronger environment-specific configuration validation
- Containerized deployment
- Expanded integration and workflow testing
- Improved procurement analytics and operational reporting
- External ERP and accounting integrations
- Production-grade observability and deployment controls

These are future possibilities, not features claimed to be included in v1.0.0.

---

## Release

**Version:** [v1.0.0 — Initial Portfolio Release](https://github.com/phaneendrakatakam/ProcurePilot-AI/releases/tag/v1.0.0)

The initial release includes the procurement workflow implementation, database migrations, frontend, supporting scripts, and automated tests.

No private credentials, populated databases, or screenshots are distributed as part of the repository release.

---

## Author

**Phaneendra Katakam**

- **GitHub:** [phaneendrakatakam](https://github.com/phaneendrakatakam)
- **Portfolio:** [phaneendrakatakam.github.io](https://phaneendrakatakam.github.io/)

---

**ProcurePilot — Structured Procurement. Controlled Approvals. Traceable Decisions.**
