from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_purchase_request_approval_model_is_registered():
    model = (ROOT / "app/models/procurement.py").read_text(encoding="utf-8")

    assert "class PurchaseRequestApproval" in model
    assert 'class PurchaseRequestApproval(UUIDPrimaryKeyMixin, TimestampMixin, Base)' in model
    assert '"purchase_request_approvals"' in model
    assert '"uq_purchase_request_approval_sequence"' in model
    assert 'ForeignKey("purchase_requests.id", ondelete="CASCADE")' in model
    assert 'ForeignKey("users.id", ondelete="RESTRICT")' in model
    assert 'status: Mapped[str]' in model
    assert 'decision_comment: Mapped[str | None]' in model
    assert 'decided_at: Mapped[datetime | None]' in model


def test_purchase_request_approval_migration_is_chained_after_supplier_selection():
    migration = (
        ROOT
        / "alembic/versions/2f7c1a9e6b40_add_purchase_request_approval_workflow.py"
    ).read_text(encoding="utf-8")

    assert 'down_revision = "9d5e7f1b3c20"' in migration
    assert '"purchase_request_approvals"' in migration
    assert '"purchase_request_id"' in migration
    assert '"approver_user_id"' in migration
    assert '"approver_role"' in migration
    assert '"sequence"' in migration
    assert '"decision_comment"' in migration
    assert '"decided_at"' in migration


def test_purchase_request_model_exposes_ordered_approval_steps():
    model = (ROOT / "app/models/procurement.py").read_text(encoding="utf-8")

    assert 'approvals: Mapped[list["PurchaseRequestApproval"]]' in model
    assert 'order_by="PurchaseRequestApproval.sequence"' in model
