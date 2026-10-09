"""Read-only command-line proof of the persisted ProcurePilot demo and repair.

No database writes. Never prints credentials, supplier emails, or tokenized URLs.
Run from project root: python -m scripts.verify_e2e_repairs
"""
from __future__ import annotations

import argparse
from decimal import Decimal

from sqlalchemy import inspect, select
from sqlalchemy.orm import selectinload

from app.core.database import engine, SessionLocal
from app.models.goods_receipts import GoodsReceipt
from app.models.invoices import SupplierInvoice
from app.models.invoice_matching import SupplierInvoiceMatch
from app.models.procurement import PurchaseRequest, PurchaseOrder
from app.models.identity import User
from app.api.routes.purchase_requests import get_purchase_request_lifecycle
from app.api.routes.invoices import _summary as invoice_summary


def check(label: str, condition: bool) -> None:
    print(f"{'PASS' if condition else 'FAIL'} — {label}")
    if not condition:
        raise RuntimeError(f"Verification failed: {label}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request-number', default='PR-2026-EC293939')
    parser.add_argument('--po-number', default='PO-2026-FE113C')
    parser.add_argument('--invoice-number', default='BP-WIFI-2026-001')
    args = parser.parse_args()

    with engine.connect() as connection:
        check('Additive supplier-quotation-items table exists', inspect(connection).has_table('supplier_quotation_items'))

    with SessionLocal() as db:
        req = db.scalar(select(PurchaseRequest).where(PurchaseRequest.request_number == args.request_number))
        check('Historical purchase request preserved', req is not None)
        po = db.scalar(select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.po_number == args.po_number))
        check('Issued purchase order preserved', po is not None and po.status == 'ISSUED' and po.purchase_request_id == req.id)
        receipts = db.scalars(select(GoodsReceipt).where(GoodsReceipt.purchase_order_id == po.id, GoodsReceipt.status == 'POSTED')).all()
        check('Posted goods receipt preserved', len(receipts) > 0)
        invoice = db.scalar(select(SupplierInvoice).options(selectinload(SupplierInvoice.vendor), selectinload(SupplierInvoice.purchase_order)).where(
            SupplierInvoice.invoice_number == args.invoice_number, SupplierInvoice.purchase_order_id == po.id
        ))
        check('Paid invoice and payment reference preserved', invoice is not None and invoice.status == 'PAID' and bool(invoice.payment_reference))
        check('Payment timestamp and responsible user preserved', invoice.paid_at is not None and invoice.paid_by_user_id is not None)
        match = db.scalar(select(SupplierInvoiceMatch).where(SupplierInvoiceMatch.invoice_id == invoice.id))
        check('Three-way match preserved', match is not None and match.result == 'MATCHED')
        summary = invoice_summary(invoice)
        check('Invoice API summary includes payment fields', summary.payment_reference == invoice.payment_reference and summary.paid_at == invoice.paid_at)
        owner = db.scalar(select(User).where(User.id == req.requester_id))
        report = get_purchase_request_lifecycle(req.id, actor=owner, db=db)
        check('Lifecycle returns PAID without rewriting request status', report['overall_status'] == 'PAID' and report['request_status'] == req.status)
        check('All eight lifecycle stages recognized', len(report['steps']) == 8 and all(s['state'] == 'DONE' for s in report['steps']))
        print('PASS — Historical fully-paid E2E transaction verified without database writes')
        print('Legacy PO lines kept:', len(po.items), '(intentionally not rewritten)')


if __name__ == '__main__':
    main()
