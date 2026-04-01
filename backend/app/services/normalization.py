import re

# Known chain prefixes that collapse to canonical names
STORE_CHAINS: dict[str, str] = {
    "walmart": "Walmart",
    "wal-mart": "Walmart",
    "costco": "Costco",
    "target": "Target",
    "loblaws": "Loblaws",
    "metro": "Metro",
    "safeway": "Safeway",
    "whole foods": "Whole Foods",
    "dollarama": "Dollarama",
    "shoppers drug mart": "Shoppers Drug Mart",
    "no frills": "No Frills",
    "sobeys": "Sobeys",
}

# Patterns to strip from item names
JUNK_SUFFIXES = re.compile(
    r"\s+(?:\d{8,}|[A-Z]{2,3}\d{5,}|\d+\.?\d*\s*(?:g|kg|ml|l|oz|lb))\s*$",
    re.IGNORECASE,
)


def normalize_store_name(name: str) -> str:
    """Normalize a store name: check known chains, otherwise title-case."""
    cleaned = " ".join(name.split()).strip()
    lower = cleaned.lower()

    for prefix, canonical in STORE_CHAINS.items():
        if lower.startswith(prefix):
            return canonical

    return cleaned.title()


def normalize_item_name(name: str) -> str:
    """Normalize a receipt line item name: collapse whitespace, strip junk, title-case."""
    cleaned = " ".join(name.split()).strip()
    cleaned = JUNK_SUFFIXES.sub("", cleaned)
    return cleaned.title()
