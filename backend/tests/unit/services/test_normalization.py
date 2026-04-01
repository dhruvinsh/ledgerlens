from app.services.normalization import normalize_item_name, normalize_store_name


def test_walmart_variants():
    assert normalize_store_name("walmart supercenter #1234") == "Walmart"
    assert normalize_store_name("WAL-MART STORE") == "Walmart"
    assert normalize_store_name("Walmart") == "Walmart"


def test_known_chains():
    assert normalize_store_name("costco wholesale") == "Costco"
    assert normalize_store_name("LOBLAWS #456") == "Loblaws"
    assert normalize_store_name("no frills east side") == "No Frills"
    assert normalize_store_name("shoppers drug mart downtown") == "Shoppers Drug Mart"


def test_unknown_store_title_case():
    assert normalize_store_name("bob's corner store") == "Bob'S Corner Store"
    assert normalize_store_name("ACME FOODS") == "Acme Foods"


def test_item_name_collapse_whitespace():
    assert normalize_item_name("  ORGANIC   MILK  ") == "Organic Milk"


def test_item_name_strip_barcode():
    assert normalize_item_name("CHEESE CHEDDAR 12345678") == "Cheese Cheddar"


def test_item_name_strip_weight():
    assert normalize_item_name("YOGURT 500g") == "Yogurt"
    assert normalize_item_name("FLOUR 2.5kg") == "Flour"


def test_item_name_title_case():
    assert normalize_item_name("WHOLE WHEAT BREAD") == "Whole Wheat Bread"
