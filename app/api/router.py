from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.audit import router as audit_router
from app.api.routes.automations import router as automations_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.master_data import router as master_data_router
from app.api.routes.purchase_request_approvals import router as purchase_request_approvals_router
from app.api.routes.purchase_orders import router as purchase_orders_router
from app.api.routes.purchase_requests import router as purchase_requests_router
from app.api.routes.rfqs import router as rfqs_router
from app.api.routes.quotations import router as quotations_router
from app.api.routes.supplier_selections import router as supplier_selections_router
from app.api.routes.supplier_responses import router as supplier_responses_router
from app.api.routes.goods_receipts import router as goods_receipts_router
from app.api.routes.invoices import router as invoices_router
from app.api.routes.invoice_matching import router as invoice_matching_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(master_data_router)
api_router.include_router(audit_router)
api_router.include_router(automations_router)
api_router.include_router(dashboard_router)
api_router.include_router(purchase_requests_router)
api_router.include_router(rfqs_router)
api_router.include_router(quotations_router)
api_router.include_router(supplier_selections_router)
api_router.include_router(supplier_responses_router)
api_router.include_router(goods_receipts_router)
api_router.include_router(invoices_router)
api_router.include_router(invoice_matching_router)
api_router.include_router(purchase_request_approvals_router)

api_router.include_router(purchase_orders_router)
