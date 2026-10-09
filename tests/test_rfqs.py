from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_rfq_backend_and_schema_are_implemented():
    route = (ROOT / "app/api/routes/rfqs.py").read_text(encoding="utf-8")
    schema = (ROOT / "app/schemas/rfqs.py").read_text(encoding="utf-8")
    model = (ROOT / "app/models/procurement.py").read_text(encoding="utf-8")
    router = (ROOT / "app/api/router.py").read_text(encoding="utf-8")
    assert '@router.post("", response_model=RFQDetail, status_code=status.HTTP_201_CREATED)' in route
    assert '@router.post("/{rfq_id}/send", response_model=RFQDetail)' in route
    assert "RFQ_CREATED" in route and "RFQ_SENT" in route
    assert "sourcing.manage" in route
    assert "class RFQCreate" in schema and "vendor_ids" in schema
    assert "class RFQ" in model and "class RFQSupplier" in model
    assert "rfqs_router" in router

def test_rfq_migration_is_chained_after_supplier_master():
    migration = (ROOT / "alembic/versions/7b2c9d4e1f60_add_rfqs.py").read_text(encoding="utf-8")
    assert 'down_revision = "6e8f2a1c4d90"' in migration
    assert '"rfqs"' in migration and '"rfq_suppliers"' in migration
