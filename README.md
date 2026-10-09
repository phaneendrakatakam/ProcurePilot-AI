# ProcurePilot

Controlled enterprise procurement and accounts-payable workflow platform built with FastAPI, PostgreSQL, SQLAlchemy, Alembic, and a role-aware web UI.

## End-to-end workflow

1. Employee creates a Purchase Request
2. Procurement Analyst starts sourcing
3. RFQ is created and sent to suppliers
4. Supplier quotations are captured and compared
5. Supplier is selected
6. Manager approval
7. Procurement Head approval
8. Finance approval
9. Purchase Order is created
10. Procurement Head issues the PO
11. Goods Receiver posts the Goods Receipt
12. AP Analyst captures and validates the supplier invoice
13. 3-way match checks PO, accepted receipt, and invoice
14. Finance Manager reviews the cleared invoice and finalizes payment
15. Invoice becomes `PAID` with an auditable payment reference

## Controls

- Database-backed RBAC by role and permission
- Deterministic procurement and financial workflow
- Human/system audit trail
- Finance payment finalization is restricted to `finance.review`
- Payment cannot be finalized without a successful 3-way match
- Payment reference, timestamp, and finalizing user are persisted
- Supplier invoice exceptions remain blocked from payment finalization

## Local setup

Copy `.env.example` to `.env`, configure PostgreSQL, run Alembic migrations, seed demo data, then start FastAPI. If the PostgreSQL password contains URL-reserved characters such as `@`, URL-encode the password in `DATABASE_URL` (for example `@` becomes `%40`).

```bash
alembic upgrade head
python -m app.seed.bootstrap
uvicorn app.main:app --reload
```

Do not commit `.env` or production credentials.
