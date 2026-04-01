from app.services.heuristic import extract_receipt_data


def test_extract_total():
    text = "MILK 5.49\nBREAD 3.99\nSUBTOTAL 9.48\nHST 1.23\nTOTAL 10.71"
    result = extract_receipt_data(text)
    assert result["total_cents"] == 1071


def test_extract_tax():
    text = "ITEMS\nHST 2.50\nTOTAL 20.00"
    result = extract_receipt_data(text)
    assert result["tax_cents"] == 250


def test_subtotal_not_confused_with_total():
    text = "SUBTOTAL 9.48\nTAX 1.23\nTOTAL 10.71"
    result = extract_receipt_data(text)
    assert result["total_cents"] == 1071
    assert result["tax_cents"] == 123


def test_extract_date_iso():
    text = "STORE\n2026-03-25\nTOTAL 10.00"
    result = extract_receipt_data(text)
    assert result["transaction_date"] == "2026-03-25"


def test_extract_date_us_format():
    text = "STORE\n03/25/2026\nTOTAL 10.00"
    result = extract_receipt_data(text)
    assert result["transaction_date"] == "2026-03-25"


def test_extract_store_name():
    text = "WALMART SUPERCENTRE\n123 Main St\nTOTAL 50.00"
    result = extract_receipt_data(text)
    assert result["store_name"] == "WALMART SUPERCENTRE"


def test_extract_line_items():
    text = "MILK 2L 5.49\nBREAD 3.99\nSUBTOTAL 9.48\nTOTAL 9.48"
    result = extract_receipt_data(text)
    assert len(result["line_items"]) == 2
    assert result["line_items"][0]["name"] == "MILK 2L"
    assert result["line_items"][0]["total_price_cents"] == 549


def test_excludes_total_lines_from_items():
    text = "ITEM A 10.00\nSUBTOTAL 10.00\nTAX 1.30\nTOTAL 11.30"
    result = extract_receipt_data(text)
    names = [li["name"] for li in result["line_items"]]
    assert "SUBTOTAL" not in " ".join(names).upper()
    assert "TOTAL" not in " ".join(names).upper()


def test_empty_text():
    result = extract_receipt_data("")
    assert result["total_cents"] is None
    assert result["line_items"] == []


def test_caps_line_items_at_50():
    lines = "\n".join(f"ITEM{i} {i}.99" for i in range(60))
    result = extract_receipt_data(lines)
    assert len(result["line_items"]) <= 50
