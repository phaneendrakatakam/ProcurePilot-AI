"""Focused regression checks for the consolidated ProcurePilot repair.

All database tests use their own in-memory SQLite database; they never touch
DATABASE_URL or modify a real purchase order/invoice.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.base import Base
import app.models  # noqa: F401 - load all ORM models before metadata.create_all
from app.models.identity import User, Vendor
from app.models.procurement import (
    PurchaseRequest, PurchaseRequestItem, RFQ, RFQSupplier,
    SupplierQuotation, SupplierQuotationItem, SupplierSelection,
    PurchaseRequestApproval, PurchaseOrder, PurchaseOrderItem,
)
from app.models.goods_receipts import GoodsReceipt, GoodsReceiptItem
from app.models.invoices import SupplierInvoice
from app.models.invoice_matching import SupplierInvoiceMatch
from app.schemas.quotations import QuotationLineInput
from app.services.quotation_lines import normalized_lines
from app.api.routes import invoices as invoices_route
from app.api.routes import purchase_orders as purchase_orders_route
from app.api.routes import purchase_requests as requests_route


def _request_items():
    return [
        SimpleNamespace(id=uuid.uuid4(), name="Access Point", quantity=Decimal("6.00")),
        SimpleNamespace(id=uuid.uuid4(), name="Network Switch", quantity=Decimal("2.00")),
    ]


def test_two_item_quote_preserves_individual_prices():
    items = _request_items()
    data = [
        QuotationLineInput(request_item_id=items[0].id, quantity=6, unit_price=18000),
        QuotationLineInput(request_item_id=items[1].id, quantity=2, unit_price=13000),
    ]
    lines = normalized_lines(items, data)
    assert [line[3] for line in lines] == [Decimal("108000.00"), Decimal("26000.00")]
    assert sum(line[3] for line in lines) == Decimal("134000.00")


@pytest.mark.parametrize("case", ["missing", "duplicate", "wrong_quantity", "foreign_item"])
def test_quote_rejects_incomplete_or_bad_items(case):
    items = _request_items()
    data = [
        QuotationLineInput(request_item_id=items[0].id, quantity=6, unit_price=18000),
        QuotationLineInput(request_item_id=items[1].id, quantity=2, unit_price=13000),
    ]
    if case == "missing":
        data.pop()
    elif case == "duplicate":
        data[1] = data[0]
    elif case == "wrong_quantity":
        data[1] = QuotationLineInput(request_item_id=items[1].id, quantity=1, unit_price=13000)
    else:
        data[1] = QuotationLineInput(request_item_id=uuid.uuid4(), quantity=2, unit_price=13000)
    with pytest.raises(ValueError):
        normalized_lines(items, data)


@pytest.fixture
def isolated_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _seed_business_flow(db):
    owner = User(email="owner@demo.test", full_name="Owner", password_hash="test")
    analyst = User(email="buyer@demo.test", full_name="Buyer", password_hash="test")
    vendor = Vendor(vendor_code="V-TEST", legal_name="Demo Supplier", email="supplier@demo.test")
    db.add_all([owner, analyst, vendor])
    db.flush()
    request = PurchaseRequest(
        request_number="PR-TEST-001", requester_id=owner.id, title="Office WiFi",
        status="APPROVED", budget_check_status="PASS", policy_check_status="PASS",
        currency="INR", estimated_total=Decimal("150000"),
    )
    request.items = [
        PurchaseRequestItem(name="AP", quantity=Decimal("6"), unit_price=Decimal("20000")),
        PurchaseRequestItem(name="Switch", quantity=Decimal("2"), unit_price=Decimal("15000")),
    ]
    db.add(request)
    db.flush()
    rfq = RFQ(rfq_number="RFQ-TEST", request_id=request.id, status="SENT", response_deadline=datetime(2026, 12, 1, tzinfo=timezone.utc), created_by_user_id=analyst.id)
    db.add(rfq)
    db.flush()
    supplier = RFQSupplier(rfq_id=rfq.id, vendor_id=vendor.id, status="RESPONDED")
    db.add(supplier)
    db.flush()
    quotation = SupplierQuotation(
        rfq_id=rfq.id, rfq_supplier_id=supplier.id, currency="INR", quoted_quantity=Decimal("1"),
        unit_price=Decimal("134000"), subtotal=Decimal("134000"), tax_amount=Decimal("24120"), total_amount=Decimal("158120"),
        delivery_days=10, valid_until=date(2026, 12, 1), status="RECEIVED", submission_source="SUPPLIER_PORTAL",
    )
    db.add(quotation)
    db.flush()
    for request_item, cost in zip(request.items, [Decimal("18000"), Decimal("13000")]):
        quotation.items.append(SupplierQuotationItem(
            request_item_id=request_item.id, quantity=request_item.quantity,
            unit_price=cost, line_total=request_item.quantity * cost,
        ))
    db.flush()
    selection = SupplierSelection(rfq_id=rfq.id, rfq_supplier_id=supplier.id, quotation_id=quotation.id, rationale="Lowest price", selected_by_user_id=analyst.id)
    db.add(selection)
    for seq, role in enumerate(["MANAGER", "PROCUREMENT_HEAD", "FINANCE_MANAGER"], 1):
        db.add(PurchaseRequestApproval(purchase_request_id=request.id, approver_user_id=analyst.id, approver_role=role, sequence=seq, status="APPROVED"))
    db.flush()
    return owner, analyst, request, vendor, selection, quotation


def test_quote_items_are_persisted_without_aggregation(isolated_session):
    db = isolated_session
    _, _, request, _, _, quotation = _seed_business_flow(db)
    db.flush()
    saved = db.scalars(select(SupplierQuotationItem).where(SupplierQuotationItem.supplier_quotation_id == quotation.id)).all()
    assert len(saved) == 2
    assert {line.request_item_id for line in saved} == {item.id for item in request.items}
    assert sum((line.line_total for line in saved), Decimal("0")) == quotation.subtotal


def test_lifecycle_reports_paid_without_mutating_original_request(isolated_session, monkeypatch):
    db = isolated_session
    owner, analyst, request, vendor, selection, quotation = _seed_business_flow(db)
    po = PurchaseOrder(
        po_number="PO-TEST", purchase_request_id=request.id,
        supplier_selection_id=selection.id, vendor_id=vendor.id,
        currency="INR", status="ISSUED", subtotal=Decimal("134000"), tax_amount=Decimal("24120"),
        total_amount=Decimal("158120"), delivery_days=10, payment_terms_days=45,
        po_date=date(2026, 10, 9), created_by_user_id=analyst.id,
    )
    db.add(po)
    db.flush()
    for line in quotation.items:
        po.items.append(PurchaseOrderItem(
            request_item_id=line.request_item_id, name=line.request_item.name, quantity=line.quantity,
            unit_price=line.unit_price, line_total=line.line_total,
        ))
    db.flush()
    receipt = GoodsReceipt(receipt_number="GR-TEST", purchase_order_id=po.id, received_by_user_id=analyst.id, receipt_date=date(2026, 10, 9), status="POSTED")
    db.add(receipt)
    db.flush()
    for line in po.items:
        db.add(GoodsReceiptItem(goods_receipt_id=receipt.id, purchase_order_item_id=line.id,
            received_quantity=line.quantity, accepted_quantity=line.quantity, rejected_quantity=Decimal("0")))
    invoice = SupplierInvoice(invoice_number="BILL-TEST", purchase_order_id=po.id, vendor_id=vendor.id,
        invoice_date=date(2026, 10, 9), due_date=date(2026, 11, 23), currency="INR", status="PAID",
        subtotal=Decimal("134000"), tax_amount=Decimal("24120"), total_amount=Decimal("158120"),
        payment_reference="PAY-TEST", paid_at=datetime.now(timezone.utc), paid_by_user_id=analyst.id,
        created_by_user_id=analyst.id)
    db.add(invoice)
    db.flush()
    db.add(SupplierInvoiceMatch(invoice_id=invoice.id, purchase_order_id=po.id, result="MATCHED",
        po_quantity=Decimal("8"), received_quantity=Decimal("8"), accepted_quantity=Decimal("8"),
        invoice_quantity=Decimal("8"), quantity_variance=Decimal("0"), po_amount=Decimal("134000"),
        invoice_amount=Decimal("134000"), price_variance=Decimal("0"), price_variance_percent=Decimal("0"),
        quantity_tolerance=Decimal("0"), price_tolerance_percent=Decimal("0"), evaluated_by_user_id=analyst.id))
    db.flush()
    monkeypatch.setattr(requests_route, "_require_read", lambda actor, req: None)
    snapshot = requests_route.get_purchase_request_lifecycle(request.id, actor=owner, db=db)
    assert snapshot["request_status"] == "APPROVED"
    assert snapshot["overall_status"] == "PAID"
    assert len(snapshot["steps"]) == 8
    assert all(step["state"] == "DONE" for step in snapshot["steps"])
    assert snapshot["steps"][-1]["detail"] == "PAY-TEST"


def test_issued_po_terms_cannot_be_edited(isolated_session):
    db = isolated_session
    _, analyst, request, vendor, selection, quotation = _seed_business_flow(db)
    po = PurchaseOrder(po_number="PO-LOCKED", purchase_request_id=request.id,
        supplier_selection_id=selection.id, vendor_id=vendor.id, currency="INR", status="ISSUED",
        subtotal=quotation.subtotal, tax_amount=quotation.tax_amount, total_amount=quotation.total_amount,
        delivery_days=10, payment_terms_days=41, po_date=date(2026, 10, 9), created_by_user_id=analyst.id)
    db.add(po)
    db.flush()
    with pytest.raises(HTTPException) as ex:
        purchase_orders_route.correct_purchase_order_payment_terms(po.id,
            purchase_orders_route.PurchaseOrderTermsCorrection(payment_terms_days=45, explanation="New vendor agreement"),
            actor=analyst, db=db)
    assert ex.value.status_code == 409
    assert po.payment_terms_days == 41


def test_invoice_payment_fields_always_serialized():
    vendor = SimpleNamespace(vendor_code="V-TEST", legal_name="Test Vendor")
    po = SimpleNamespace(po_number="PO-TEST")
    actor_id = uuid.uuid4()
    obj = SimpleNamespace(
        id=uuid.uuid4(), invoice_number="TEST", vendor_id=uuid.uuid4(), vendor=vendor,
        purchase_order_id=uuid.uuid4(), purchase_order=po,
        invoice_date=date(2026, 10, 9), due_date=date(2026, 11, 19), currency="INR",
        subtotal=Decimal("100"), tax_amount=Decimal("18"), total_amount=Decimal("118"),
        status="RECEIVED", created_by_user_id=actor_id,
        validated_at=None, payment_reference=None, paid_at=None, paid_by_user_id=None,
        created_at=datetime.now(timezone.utc),
    )
    assert invoices_route._summary(obj).payment_reference is None
    obj.status = "PAID"
    obj.payment_reference = "PAY-XYZ"
    obj.paid_at = datetime.now(timezone.utc)
    obj.paid_by_user_id = actor_id
    assert invoices_route._summary(obj).paid_by_user_id == actor_id
    assert invoices_route._summary(obj).payment_reference == "PAY-XYZ"


def test_create_po_from_itemized_quote_generates_two_physical_lines(isolated_session):
    from app.schemas.purchase_orders import PurchaseOrderCreate
    db = isolated_session
    _, analyst, request, vendor, selection, quote = _seed_business_flow(db)
    po = purchase_orders_route.create_purchase_order(
        PurchaseOrderCreate(supplier_selection_id=selection.id, payment_terms_days=45,
                            notes="Simulated goods for test only"),
        actor=analyst, db=db,
    )
    assert po.status == "DRAFT"
    assert po.total_amount == Decimal("158120.00")
    assert len(po.items) == 2
    assert {line.name for line in po.items} == {"AP", "Switch"}
    assert {line.quantity for line in po.items} == {Decimal("6"), Decimal("2")}
    assert sum(line.line_total for line in po.items) == po.subtotal


def test_internal_quotation_records_both_lines(isolated_session):
    from app.api.routes import quotations as quotations_route
    from app.schemas.quotations import QuotationCreate
    db = isolated_session
    analyst = User(email="analyst@demo.test", full_name="Buyer", password_hash="test")
    vendor = Vendor(vendor_code="VQ-TEST", legal_name="Supplier", email="supplierq@demo.test")
    db.add_all([analyst, vendor]); db.flush()
    request = PurchaseRequest(request_number="PRQ-TEST", requester_id=analyst.id,
        title="Two items", status="SOURCING", currency="INR")
    request.items = [PurchaseRequestItem(name="AP", quantity=Decimal("6")),
                     PurchaseRequestItem(name="Switch", quantity=Decimal("2"))]
    db.add(request); db.flush()
    rfq = RFQ(rfq_number="RFQQ-TEST", request_id=request.id, status="SENT",
        response_deadline=datetime(2026, 12, 1, tzinfo=timezone.utc), created_by_user_id=analyst.id)
    db.add(rfq); db.flush()
    invite = RFQSupplier(rfq_id=rfq.id, vendor_id=vendor.id, status="SENT")
    db.add(invite); db.flush()
    payload = QuotationCreate(rfq_id=rfq.id, rfq_supplier_id=invite.id, currency="INR",
        quoted_quantity=1, unit_price=134000, tax_amount=24120, delivery_days=10,
        valid_until=date(2026, 12, 1), items=[
            QuotationLineInput(request_item_id=request.items[0].id, quantity=6, unit_price=18000),
            QuotationLineInput(request_item_id=request.items[1].id, quantity=2, unit_price=13000),
        ])
    answer = quotations_route.record_quotation(payload, actor=analyst, db=db)
    assert answer.total_amount == Decimal("158120.00")
    assert len(answer.items) == 2
    assert [i.item_name for i in answer.items] == ["AP", "Switch"]


def test_multi_item_internal_quote_cannot_be_aggregate_only(isolated_session):
    from app.api.routes import quotations as quotations_route
    from app.schemas.quotations import QuotationCreate
    db = isolated_session
    analyst = User(email="analyst2@demo.test", full_name="Buyer", password_hash="test")
    vendor = Vendor(vendor_code="VQ2-TEST", legal_name="Supplier", email="supplierq2@demo.test")
    db.add_all([analyst,vendor]); db.flush()
    request = PurchaseRequest(request_number="PRQ2-TEST", requester_id=analyst.id,
        title="Two items", status="SOURCING", currency="INR")
    request.items = [PurchaseRequestItem(name="AP", quantity=Decimal("6")),
                     PurchaseRequestItem(name="Switch", quantity=Decimal("2"))]
    db.add(request); db.flush()
    rfq = RFQ(rfq_number="RFQ2-TEST", request_id=request.id, status="SENT",
        response_deadline=datetime(2026, 12, 1, tzinfo=timezone.utc), created_by_user_id=analyst.id)
    db.add(rfq); db.flush()
    invite = RFQSupplier(rfq_id=rfq.id, vendor_id=vendor.id, status="SENT")
    db.add(invite); db.flush()
    payload = QuotationCreate(rfq_id=rfq.id, rfq_supplier_id=invite.id, currency="INR",
        quoted_quantity=1, unit_price=134000, tax_amount=24120, delivery_days=10,
        valid_until=date(2026, 12, 1))
    with pytest.raises(HTTPException) as error:
        quotations_route.record_quotation(payload, actor=analyst, db=db)
    assert error.value.status_code == 422
