import json
import logging
import re

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You extract structured data from raw receipt OCR text.
Respond with a single JSON object only (no markdown fences, no commentary).

## Output schema

{
  "raw_store_name": "<store name exactly as it appears on the receipt>",
  "store_name": "<cleaned, title-cased official business name>",
  "store_address": "<street address, city, province/state or null>",
  "store_chain": "<parent chain/brand name or null>",
  "transaction_date": "<YYYY-MM-DD or null>",
  "currency": "<3-letter ISO code or null>",
  "subtotal_cents": <int or null>,
  "tax_cents": <int or null>,
  "total_cents": <int or null>,
  "discount_total_cents": <int or null>,
  "payment_method": "<cash|credit|debit|other or null>",
  "is_refund_receipt": <bool>,
  "tax_breakdown": [{"tax_type": "HST", "rate_percent": 13.0, "amount_cents": 1500}] or null,
  "line_items": [<see below>]
}

## Store fields

- raw_store_name: Preserve OCR text verbatim.
- store_name: The official business name. Remove store/location numbers \
(e.g. "WALMART #1234" → "Walmart"). Fix obvious OCR errors in known chains. \
Use proper title case. Do NOT include the address in the name.
- store_address: Full street address if present. Normalize to \
"123 Main St, City, Province/State". Exclude phone numbers and URLs.
- store_chain: The parent brand if the store belongs to a chain \
(e.g. "Great Canadian Superstore" → "Loblaws", "No Frills" → "Loblaws"). \
null for independent stores.

## Monetary values

All amounts MUST be integers in minor units (cents). Use null for unknown fields.

- discount_total_cents: Total savings/discounts on the receipt. Always positive.
- tax_breakdown: Array of per-tax-type entries if the receipt shows separate tax lines \
(e.g. GST + PST). Include rate_percent if printed. null if only a single "TAX" line.
- payment_method: Inferred from the payment line at the bottom of the receipt.
- is_refund_receipt: true only if the entire receipt is a return/refund transaction.

## Line items

Each item in line_items:
{
  "raw_name": "<item name exactly as printed on receipt>",
  "name": "<human-readable product name, title case>",
  "quantity": <float, default 1.0>,
  "unit_price_cents": <int or null>,
  "total_price_cents": <int>,
  "discount_cents": <int or null>,
  "is_refund": <bool>,
  "tax_code": "<H|G|P|F or null>",
  "weight_qty": "<e.g. 1.230 kg, 0.5 lb, or null>"
}

Rules for line items:
- raw_name: The item name portion only, exactly as printed on the receipt. \
Do NOT include prices, dollar amounts, tax code letters (H/G/P/F/J/D), \
UPC/SKU barcodes, or quantity prefixes. Only the name text. \
Example: "CLR MOULINT TP $6.72 J" → raw_name: "CLR MOULINT TP".
- name: Expand common receipt abbreviations to full product names \
(e.g. "GV 2% MLK 4L" → "Great Value 2% Milk 4L", "ORG BNA" → "Organic Banana"). \
Use proper title case. If you recognise the product, use its full retail name.
- quantity: Parse "2 x", "2@", or quantity prefixes. Default 1.0.
- unit_price_cents: Price per unit. If only total is shown, divide by quantity.
- discount_cents: Savings for this item if a discount/coupon line follows it \
(e.g. "SAVE $1.00", "MFR COUPON", "-1.00"). Always a positive integer. null if none.
- is_refund: true if this is a returned/refunded item (negative price, "RETURN", "RFND"). \
Keep total_price_cents positive; the flag marks it as a refund.
- tax_code: Tax indicator letter printed next to the item ("H" HST, "G" GST, \
"P" PST, "F" tax-free/exempt). null if not visible.
- weight_qty: For weighted items (produce, deli), the weight string. null for count items.

IMPORTANT rules:
- Do NOT include subtotal, tax, total, payment, or change lines as items.
- Combine multi-line items (name on one line, price on next) into one entry.
- Associate discount/coupon lines with the preceding item — merge into discount_cents.
- For BOGO or "buy X get Y" deals, include both items with appropriate discounts.
- Mark refund-section items with is_refund: true."""


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _build_client(
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
) -> OpenAI:
    return OpenAI(
        base_url=base_url if base_url is not None else settings.LLM_BASE_URL,
        api_key=(api_key or settings.LLM_API_KEY) or "not-needed",
        timeout=timeout if timeout is not None else settings.LLM_TIMEOUT_SECONDS,
        max_retries=max_retries if max_retries is not None else settings.LLM_MAX_RETRIES,
    )


def _build_user_content(
    raw_text: str,
    known_stores: list[str] | None = None,
    known_products: list[str] | None = None,
) -> str:
    """Build the user message with OCR text and optional known-entity context."""
    parts = [raw_text]

    if known_stores:
        store_list = ", ".join(known_stores[:50])
        parts.append(
            f"\n---\nKnown stores in the system: [{store_list}]\n"
            "If this receipt matches one of these stores, use that exact store_name."
        )

    if known_products:
        product_list = ", ".join(known_products[:100])
        parts.append(
            f"\n---\nKnown products in the system: [{product_list}]\n"
            "If a line item matches a known product, use that exact name."
        )

    return "\n".join(parts)


def extract_receipt_data(
    raw_text: str,
    base_url: str | None = None,
    model_name: str | None = None,
    api_key: str | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
    known_stores: list[str] | None = None,
    known_products: list[str] | None = None,
) -> dict:
    """Extract structured receipt data from OCR text using an LLM.

    Returns a dict with keys: raw_store_name, store_name, store_address,
    store_chain, transaction_date, currency, subtotal_cents, tax_cents,
    total_cents, discount_total_cents, payment_method, is_refund_receipt,
    tax_breakdown, line_items.
    Returns {} on failure (caller should fall back to heuristic).
    """
    effective_url = base_url if base_url is not None else settings.LLM_BASE_URL
    effective_model = model_name or settings.LLM_MODEL
    client = _build_client(base_url, api_key, timeout, max_retries)

    logger.info("LLM extraction: model=%s base_url=%s", effective_model, effective_url)

    user_content = _build_user_content(raw_text, known_stores, known_products)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    # Try with JSON mode first; fall back without it if the model rejects the parameter
    try:
        response = client.chat.completions.create(
            model=effective_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
    except APIStatusError as e:
        # 400/422 likely means model doesn't support JSON mode — retry without it
        logger.warning(
            "JSON mode not supported by %s (status %s), retrying without it",
            effective_model, e.status_code,
        )
        try:
            response = client.chat.completions.create(
                model=effective_model,
                messages=messages,
                temperature=0.0,
            )
        except Exception as e2:
            logger.warning("LLM extraction failed on retry: %s", e2)
            return {}
    except (APIConnectionError, APITimeoutError) as e:
        # Connection or timeout — don't silently swallow, let caller know
        logger.error("LLM connection/timeout error: %s", e)
        return {}
    except Exception as e:
        logger.error("LLM unexpected error: %s", e)
        return {}

    content = response.choices[0].message.content
    if not content:
        return {}

    content = _strip_markdown_fences(content)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("LLM returned invalid JSON: %.200s", content)
        return {}

    return data  # type: ignore[no-any-return]
