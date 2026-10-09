from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_invoice_model_schema_and_migration_are_defined():
    model = (ROOT / "app/models/invoices.py").read_text(encoding="utf-8")
    schema = (ROOT / "app/schemas/invoices.py").read_text(encoding="utf-8")
    migration = (ROOT / "alembic/versions/8b5d2f7c1a40_add_supplier_invoices.py").read_text(encoding="utf-8")

    assert '__tablename__ = "supplier_invoices"' in model
    assert '__tablename__ = "supplier_invoice_items"' in model
    assert 'purchase_order_id' in model
    assert 'vendor_id' in model
    assert 'invoice_number' in model
    assert 'class SupplierInvoiceCreate' in schema
    assert 'class SupplierInvoiceDetail' in schema
    assert 'class InvoicePurchaseOrder' in schema
    assert 'supplier_invoices' in migration
    assert 'supplier_invoice_items' in migration
    assert 'uq_supplier_invoice_vendor_number' in migration


def test_invoice_api_lifecycle_and_business_guards_are_wired():
    route = (ROOT / "app/api/routes/invoices.py").read_text(encoding="utf-8")
    assert 'router = APIRouter(prefix="/invoices"' in route
    assert '@router.get("/purchase-orders"' in route
    assert '@router.get("", response_model=list[SupplierInvoiceSummary])' in route
    assert '@router.post("", response_model=SupplierInvoiceDetail, status_code=status.HTTP_201_CREATED)' in route
    assert '@router.post("/{invoice_id}/validate"' in route
    assert '@router.post("/{invoice_id}/send-to-matching"' in route
    assert 'require_permissions("invoices.review")' in route
    assert 'Invoice supplier must match the purchase order supplier' in route
    assert 'Invoice currency must match the purchase order currency' in route
    assert 'status="RECEIVED"' in route
    assert 'invoice.status = "VALIDATING"' in route
    assert 'invoice.status = "MATCHING"' in route
    assert 'SUPPLIER_INVOICE_RECEIVED' in route
    assert 'SUPPLIER_INVOICE_VALIDATED' in route
    assert 'SUPPLIER_INVOICE_SENT_TO_MATCHING' in route


def test_invoice_schema_totals_and_dates_are_validated():
    schema = (ROOT / "app/schemas/invoices.py").read_text(encoding="utf-8")
    assert 'Invoice line total must equal quantity multiplied by unit price' in schema
    assert 'Invoice subtotal must equal the sum of invoice line totals' in schema
    assert 'Invoice total must equal subtotal plus tax' in schema
    assert 'Invoice due date cannot be before the invoice date' in schema


def test_invoice_permissions_and_ap_workspace_are_wired():
    seed = (ROOT / "app/seed/bootstrap.py").read_text(encoding="utf-8")
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8-sig")
    css = (ROOT / "app/web/static/css/app.css").read_text(encoding="utf-8")
    router = (ROOT / "app/api/router.py").read_text(encoding="utf-8")

    assert '"invoices.review"' in seed
    assert '"AP_ANALYST": {"invoices.review"}' in seed
    assert 'from app.api.routes.invoices import router as invoices_router' in router
    assert 'api_router.include_router(invoices_router)' in router
    assert 'function renderInvoices()' in js
    assert 'function renderInvoiceDetail' in js
    assert 'function openCreateInvoice' in js
    assert 'api("/invoices")' in js
    assert 'api("/invoices/purchase-orders")' in js
    assert 'Record supplier invoice' in js
    assert 'Validate invoice' in js
    assert 'Send to 3-way matching' in js
    assert 'data-invoice-search' in js
    assert 'data-invoice-status-filter' in js
    assert '.invoice-toolbar' in css


def test_invoice_lifecycle_uses_invoice_states_without_implementing_matching_logic():
    js = (ROOT / "app/web/static/js/app.js").read_text(encoding="utf-8-sig")
    route = (ROOT / "app/api/routes/invoices.py").read_text(encoding="utf-8")
    for status in ["RECEIVED", "VALIDATING", "MATCHING", "EXCEPTION", "READY_FOR_PAYMENT"]:
        assert status in js or status in route
    assert '3-way matching' in js

def test_invoice_schema_has_repair_migration():
    repair = (
        ROOT / "alembic/versions/9c6e1f4a2b70_repair_supplier_invoice_tables.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "9c6e1f4a2b70"' in repair
    assert 'down_revision = "8b5d2f7c1a40"' in repair
    assert 'inspector.has_table("supplier_invoices")' in repair
    assert 'inspector.has_table("supplier_invoice_items")' in repair
    assert 'supplier_invoices' in repair
    assert 'supplier_invoice_items' in repair
