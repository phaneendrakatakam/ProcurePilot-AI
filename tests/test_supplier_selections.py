from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_supplier_selection_backend_and_schema_are_implemented():
    route = (ROOT / "app/api/routes/supplier_selections.py").read_text(encoding="utf-8")
    schema = (ROOT / "app/schemas/supplier_selections.py").read_text(encoding="utf-8")
    model = (ROOT / "app/models/procurement.py").read_text(encoding="utf-8")
    router = (ROOT / "app/api/router.py").read_text(encoding="utf-8")

    assert 'prefix="/supplier-selections"' in route
    assert "def list_supplier_selections" in route
    assert "def get_supplier_selection_for_rfq" in route
    assert "def select_supplier" in route
    assert 'Depends(require_permissions("sourcing.manage"))' in route
    assert 'rfq.request.status = "SUPPLIER_SELECTED"' in route
    assert "SUPPLIER_SELECTED" in route
    assert "A supplier must have a recorded quotation before selection" in route
    assert 'invitation.status not in {"SENT", "RESPONDED"}' in route
    assert "RESPONDED" in route
    assert "A supplier has already been selected for this RFQ" in route
    assert "class SupplierSelectionCreate" in schema
    assert "class SupplierSelectionSummary" in schema
    assert "class SupplierSelection" in model
    assert "uq_supplier_selection_rfq" in model
    assert "supplier_selections_router" in router


def test_supplier_selection_migration_is_chained_after_quotations():
    migration = (ROOT / "alembic/versions/9d5e7f1b3c20_add_supplier_selection.py").read_text(encoding="utf-8")
    assert 'down_revision = "8c4e1a7d2b90"' in migration
    assert '"supplier_selections"' in migration
    assert '"quotation_id"' in migration
    assert '"selected_by_user_id"' in migration
