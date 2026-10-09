"""Financially safe itemized supplier pricing. No modifications to historical quotations."""
from decimal import Decimal


def normalized_lines(request_items, submitted):
    """Return checked (request item, qty, price, amount) tuples; all requested items mandatory."""
    by_id = {str(item.id): item for item in request_items}
    if not by_id or not submitted or len(submitted) != len(by_id):
        raise ValueError("A separate quotation line is required for every requested item.")
    seen = set()
    result = []
    for line in submitted:
        key = str(line.request_item_id)
        if key not in by_id or key in seen:
            raise ValueError("Quotation lines must reference distinct items from this request.")
        seen.add(key)
        qty, price = Decimal(line.quantity), Decimal(line.unit_price)
        if qty <= 0 or price <= 0 or qty != Decimal(by_id[key].quantity):
            raise ValueError("Quoted quantities must match the requested quantities and prices must be positive.")
        result.append((by_id[key], qty, price, (qty * price).quantize(Decimal("0.01"))))
    return result
