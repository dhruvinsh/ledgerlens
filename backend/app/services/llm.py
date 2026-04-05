import json
import logging
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.core.config import settings
from app.services.image_utils import get_image_content_blocks

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_jinja_env = Environment(
    loader=FileSystemLoader(_PROMPTS_DIR),
    autoescape=select_autoescape([]),
    keep_trailing_newline=False,
    trim_blocks=True,
    lstrip_blocks=True,
)

_system_template = _jinja_env.get_template("system.md.j2")
_user_template = _jinja_env.get_template("user.md.j2")
_system_vision_template = _jinja_env.get_template("system_vision.md.j2")
_user_vision_template = _jinja_env.get_template("user_vision.md.j2")

SYSTEM_PROMPT = _system_template.render()
SYSTEM_VISION_PROMPT = _system_vision_template.render()


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
    """Render the user message template with OCR text and optional known-entity context."""
    return _user_template.render(
        raw_text=raw_text,
        known_stores=known_stores[:50] if known_stores else None,
        known_products=known_products[:100] if known_products else None,
    ).strip()


def _build_vision_user_content(
    image_content_blocks: list[dict],
    known_stores: list[str] | None = None,
    known_products: list[str] | None = None,
) -> list[dict]:
    """Build multipart user content with text instruction + image blocks."""
    text = _user_vision_template.render(
        known_stores=known_stores[:50] if known_stores else None,
        known_products=known_products[:100] if known_products else None,
    ).strip()
    return [{"type": "text", "text": text}] + image_content_blocks


def extract_receipt_data_vision(
    file_path: str,
    base_url: str | None = None,
    model_name: str | None = None,
    api_key: str | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
    known_stores: list[str] | None = None,
    known_products: list[str] | None = None,
) -> dict:
    """Extract structured receipt data by sending the image directly to a vision LLM.

    Returns a dict with the same schema as extract_receipt_data().
    Returns {} on failure (caller should fall back to text LLM or heuristic).
    """
    effective_url = base_url if base_url is not None else settings.LLM_BASE_URL
    effective_model = model_name or settings.LLM_MODEL
    client = _build_client(base_url, api_key, timeout, max_retries)

    logger.info("Vision LLM extraction: model=%s base_url=%s file=%s", effective_model, effective_url, file_path)

    try:
        image_blocks = get_image_content_blocks(file_path)
    except Exception as e:
        logger.error("Failed to encode receipt image for vision: %s", e)
        return {}

    user_content = _build_vision_user_content(image_blocks, known_stores, known_products)
    messages = [
        {"role": "system", "content": SYSTEM_VISION_PROMPT},
        {"role": "user", "content": user_content},
    ]

    try:
        response = client.chat.completions.create(
            model=effective_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
    except APIStatusError as e:
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
            logger.warning("Vision LLM extraction failed on retry: %s", e2)
            return {}
    except (APIConnectionError, APITimeoutError) as e:
        logger.error("Vision LLM connection/timeout error: %s", e)
        return {}
    except Exception as e:
        logger.error("Vision LLM unexpected error: %s", e)
        return {}

    content = response.choices[0].message.content
    if not content:
        return {}

    content = _strip_markdown_fences(content)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Vision LLM returned invalid JSON: %.200s", content)
        return {}

    return data  # type: ignore[no-any-return]


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

    try:
        response = client.chat.completions.create(
            model=effective_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
    except APIStatusError as e:
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
