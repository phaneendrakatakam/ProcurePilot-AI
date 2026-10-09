from pydantic import BaseModel, ConfigDict


class DashboardItem(BaseModel):
    model_config = ConfigDict(extra="allow")


class DashboardKPIs(BaseModel):
    open_requests: int = 0
    pending_approvals: int = 0
    rfqs_awaiting_response: int = 0
    pos_awaiting_issue: int = 0
    expected_deliveries: int = 0
    partial_receipts: int = 0
    invoice_exceptions: int = 0
    three_way_match_exceptions: int = 0
    spend: float = 0


class DashboardResponse(BaseModel):
    role: str
    title: str
    kpis: DashboardKPIs
    sections: dict[str, list[DashboardItem]]
