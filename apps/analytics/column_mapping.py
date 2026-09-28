import re

CANDIDATE_COLUMNS = {
    'revenue': ['revenue', 'sales', 'amount', 'total', 'total_amount', 'price'],
    'quantity': ['quantity', 'qty', 'units', 'units_sold'],
    'customer_id': ['customer_id', 'customer', 'client_id', 'customer_number'],
    'order_id': ['order_id', 'order', 'order_number', 'invoice_id'],
    'date': ['date', 'order_date', 'transaction_date', 'created_at', 'timestamp'],
    'region': ['region', 'territory', 'area'],
    'product': ['product', 'product_name', 'item'],
    'category': ['category', 'product_category', 'segment'],
    'profit': ['profit', 'margin', 'net_profit'],
}


def _normalize(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', str(name).lower())


def detect_column_mapping(columns: list[str]) -> dict[str, str]:
    normalized_lookup = {_normalize(col): col for col in columns}
    mapping = {}

    for canonical_field, candidates in CANDIDATE_COLUMNS.items():
        for candidate in candidates:
            normalized_candidate = _normalize(candidate)
            if normalized_candidate in normalized_lookup:
                mapping[canonical_field] = normalized_lookup[normalized_candidate]
                break

    return mapping
