import re

# Known chain prefixes that collapse to canonical names
STORE_CHAINS: dict[str, str] = {
    "walmart": "Walmart",
    "wal-mart": "Walmart",
    "wal mart": "Walmart",
    "costco": "Costco",
    "target": "Target",
    "loblaws": "Loblaws",
    "great canadian superstore": "Loblaws",
    "superstore": "Loblaws",
    "metro": "Metro",
    "safeway": "Safeway",
    "whole foods": "Whole Foods",
    "dollarama": "Dollarama",
    "shoppers drug mart": "Shoppers Drug Mart",
    "shoppers drugmart": "Shoppers Drug Mart",
    "pharmaprix": "Shoppers Drug Mart",
    "no frills": "No Frills",
    "nofrills": "No Frills",
    "sobeys": "Sobeys",
    "freshco": "Sobeys",
    "food basics": "Metro",
    "real canadian": "Loblaws",
    "valu-mart": "Loblaws",
    "valumart": "Loblaws",
    "zehrs": "Loblaws",
    "maxi": "Loblaws",
    "provigo": "Loblaws",
    "independent": "Loblaws",
    "your independent": "Loblaws",
    "t&t supermarket": "T&T Supermarket",
    "t & t": "T&T Supermarket",
    "canadian tire": "Canadian Tire",
    "home depot": "Home Depot",
    "home hardware": "Home Hardware",
    "ikea": "IKEA",
    "winners": "Winners",
    "marshalls": "Marshalls",
    "homesense": "HomeSense",
    "giant tiger": "Giant Tiger",
    "jean coutu": "Jean Coutu",
    "london drugs": "London Drugs",
    "rexall": "Rexall",
    "shoprite": "ShopRite",
    "kroger": "Kroger",
}

_STORE_NUMBER_RE = re.compile(r"\s*#?\d{3,}$")
_STORE_SUFFIX_RE = re.compile(
    r"\s*(?:supercenter|supercentre|superstore|express|marketplace)\s*$",
    re.IGNORECASE,
)

# Patterns to strip from item names
JUNK_SUFFIXES = re.compile(
    r"\s+(?:\d{8,}|[A-Z]{2,3}\d{5,}|\d+\.?\d*\s*(?:g|kg|ml|l|oz|lb))\s*$",
    re.IGNORECASE,
)


def normalize_store_name(name: str) -> tuple[str, str | None]:
    """Normalize a store name: strip numbers/suffixes, check known chains.

    Returns (normalized_name, detected_chain_or_None).
    """
    cleaned = " ".join(name.split()).strip()
    # Strip store/location numbers (e.g. "#1234", "Store 5678")
    cleaned = _STORE_NUMBER_RE.sub("", cleaned).strip()
    # Strip common suffixes
    cleaned = _STORE_SUFFIX_RE.sub("", cleaned).strip()

    lower = cleaned.lower()

    for prefix, canonical in STORE_CHAINS.items():
        if lower.startswith(prefix):
            return canonical, canonical

    return cleaned.title(), None


def normalize_item_name(name: str) -> str:
    """Normalize a receipt line item name: collapse whitespace, strip junk, title-case."""
    cleaned = " ".join(name.split()).strip()
    cleaned = JUNK_SUFFIXES.sub("", cleaned)
    return cleaned.title()
