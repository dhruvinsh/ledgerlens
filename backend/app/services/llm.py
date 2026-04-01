import json
import logging
import re

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You extract structured data from raw receipt OCR text.
Respond with a single JSON object only (no markdown fences, no commentary).
All monetary amounts MUST be integers in minor units (cents).
Use null for unknown numeric fields.
currency is a 3-letter ISO code when inferable, else null.
transaction_date must be YYYY-MM-DD or null.
line_items is an array of objects: {"name", "quantity", "unit_price_cents", "total_price_cents"}."""


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


def extract_receipt_data(
    raw_text: str,
    base_url: str | None = None,
    model_name: str | None = None,
    api_key: str | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
) -> dict:
    """Extract structured receipt data from OCR text using an LLM.

    Returns a dict with keys: store_name, store_address, transaction_date,
    currency, subtotal_cents, tax_cents, total_cents, line_items.
    Returns {} on failure (caller should fall back to heuristic).
    """
    effective_url = base_url if base_url is not None else settings.LLM_BASE_URL
    effective_model = model_name or settings.LLM_MODEL
    client = _build_client(base_url, api_key, timeout, max_retries)

    logger.info("LLM extraction: model=%s base_url=%s", effective_model, effective_url)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": raw_text},
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
