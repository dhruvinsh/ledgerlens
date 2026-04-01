import re

# Patterns for total detection
TOTAL_PATTERNS = [
    re.compile(r"(?<!SUB)(?:GRAND\s*)?TOTAL\s*[\$:]?\s*\$?([\d,]+\.?\d*)", re.IGNORECASE),
    re.compile(r"AMOUNT\s*DUE\s*[\$:]?\s*\$?([\d,]+\.?\d*)", re.IGNORECASE),
    re.compile(r"BALANCE\s*(?:DUE)?\s*[\$:]?\s*\$?([\d,]+\.?\d*)", re.IGNORECASE),
]

TAX_PATTERNS = [
    re.compile(r"(?:HST|GST|PST|TAX|VAT)\s*[\$:]?\s*\$?([\d,]+\.?\d*)", re.IGNORECASE),
]

DATE_PATTERNS = [
    re.compile(r"(\d{4}-\d{2}-\d{2})"),
    re.compile(r"(\d{2}/\d{2}/\d{4})"),
    re.compile(r"(\d{2}-\d{2}-\d{4})"),
]

# Lines that are NOT line items
EXCLUDE_PATTERNS = [
    re.compile(r"(?:sub)?total|amount|balance|change|cash|credit|debit|visa|mastercard|payment|tax|hst|gst|pst|vat", re.IGNORECASE),
]

LINE_ITEM_PATTERN = re.compile(
    r"^(.+?)\s+\$?([\d,]+\.?\d{2})\s*$"
)


def _to_cents(value_str: str) -> int | None:
    """Convert a dollar string like '12.34' or '12,34' to cents."""
    try:
        cleaned = value_str.replace(",", "")
        return int(round(float(cleaned) * 100))
    except (ValueError, TypeError):
        return None


def _normalize_date(date_str: str) -> str | None:
    """Convert various date formats to YYYY-MM-DD."""
    if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
        return date_str
    parts = re.split(r"[/\-]", date_str)
    if len(parts) == 3:
        if len(parts[2]) == 4:  # MM/DD/YYYY or DD/MM/YYYY
            return f"{parts[2]}-{parts[0]}-{parts[1]}"
    return None


def extract_receipt_data(raw_text: str) -> dict:
    """Extract receipt data using regex patterns.

    Returns the same shape as the LLM output:
    {store_name, store_address, transaction_date, currency,
     subtotal_cents, tax_cents, total_cents, line_items}
    """
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    # Store name: first non-empty, non-decorative line
    store_name = None
    for line in lines[:5]:
        if len(line) > 2 and not re.match(r"^[\*\-=\#]+$", line):
            store_name = line
            break

    # Date
    transaction_date = None
    for pattern in DATE_PATTERNS:
        for line in lines:
            m = pattern.search(line)
            if m:
                transaction_date = _normalize_date(m.group(1))
                if transaction_date:
                    break
        if transaction_date:
            break

    # Total
    total_cents = None
    for pattern in TOTAL_PATTERNS:
        for line in lines:
            m = pattern.search(line)
            if m:
                total_cents = _to_cents(m.group(1))
                if total_cents:
                    break
        if total_cents:
            break

    # Tax
    tax_cents = None
    for pattern in TAX_PATTERNS:
        for line in lines:
            m = pattern.search(line)
            if m:
                tax_cents = _to_cents(m.group(1))
                if tax_cents:
                    break
        if tax_cents:
            break

    # Subtotal
    subtotal_cents = None
    if total_cents and tax_cents:
        subtotal_cents = total_cents - tax_cents

    # Line items
    line_items: list[dict] = []
    for line in lines:
        if len(line_items) >= 50:
            break

        # Skip total/payment lines
        if any(p.search(line) for p in EXCLUDE_PATTERNS):
            continue

        m = LINE_ITEM_PATTERN.match(line)
        if m:
            name = m.group(1).strip()
            price_cents = _to_cents(m.group(2))
            if name and price_cents is not None:
                line_items.append({
                    "name": name,
                    "quantity": 1.0,
                    "unit_price_cents": price_cents,
                    "total_price_cents": price_cents,
                })

    return {
        "store_name": store_name,
        "store_address": None,
        "transaction_date": transaction_date,
        "currency": None,
        "subtotal_cents": subtotal_cents,
        "tax_cents": tax_cents,
        "total_cents": total_cents,
        "line_items": line_items,
    }
