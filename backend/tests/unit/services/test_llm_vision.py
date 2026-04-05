"""Unit tests for the vision LLM extraction path in llm.py."""
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.llm import extract_receipt_data_vision, _build_vision_user_content


# ── _build_vision_user_content ────────────────────────────────────────────────


def test_build_vision_user_content_basic():
    image_blocks = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,ABC"}}]
    parts = _build_vision_user_content(image_blocks)
    assert parts[0]["type"] == "text"
    assert "attached receipt" in parts[0]["text"].lower()
    assert parts[1] == image_blocks[0]


def test_build_vision_user_content_injects_known_stores():
    image_blocks = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,ABC"}}]
    parts = _build_vision_user_content(image_blocks, known_stores=["Walmart", "Costco"])
    text = parts[0]["text"]
    assert "Walmart" in text
    assert "Costco" in text


def test_build_vision_user_content_injects_known_products():
    image_blocks = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,ABC"}}]
    parts = _build_vision_user_content(image_blocks, known_products=["Organic Banana", "2% Milk"])
    text = parts[0]["text"]
    assert "Organic Banana" in text
    assert "2% Milk" in text


def test_build_vision_user_content_caps_known_stores():
    """known_stores is capped at 50 items."""
    image_blocks = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,ABC"}}]
    stores = [f"Store {i}" for i in range(100)]
    parts = _build_vision_user_content(image_blocks, known_stores=stores)
    text = parts[0]["text"]
    # Store 49 should be present, Store 50 should not
    assert "Store 49" in text
    assert "Store 50" not in text


def test_build_vision_user_content_multiple_image_blocks():
    image_blocks = [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,PAGE1"}},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,PAGE2"}},
    ]
    parts = _build_vision_user_content(image_blocks)
    assert parts[0]["type"] == "text"
    assert parts[1] == image_blocks[0]
    assert parts[2] == image_blocks[1]


# ── extract_receipt_data_vision ───────────────────────────────────────────────


def _make_llm_response(content: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


def _valid_receipt_json() -> dict:
    return {
        "raw_store_name": "WALMART",
        "store_name": "Walmart",
        "store_address": "123 Main St, Toronto, ON",
        "store_chain": None,
        "transaction_date": "2026-04-04",
        "currency": "CAD",
        "subtotal_cents": 1000,
        "tax_cents": 130,
        "total_cents": 1130,
        "discount_total_cents": None,
        "payment_method": "credit",
        "is_refund_receipt": False,
        "tax_breakdown": None,
        "line_items": [],
    }


def test_vision_extraction_success(tmp_path):
    fake_file = tmp_path / "receipt.jpg"
    fake_file.write_bytes(b"FAKEJPEG")

    receipt_data = _valid_receipt_json()

    with patch("app.services.llm.get_image_content_blocks") as mock_blocks, \
         patch("app.services.llm._build_client") as mock_client_fn:

        mock_blocks.return_value = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,FAKE"}}]
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_llm_response(json.dumps(receipt_data))

        result = extract_receipt_data_vision(str(fake_file))

    assert result["store_name"] == "Walmart"
    assert result["total_cents"] == 1130
    # Verify the user message was multipart (list, not string)
    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    assert isinstance(user_msg["content"], list)


def test_vision_extraction_strips_markdown_fences(tmp_path):
    fake_file = tmp_path / "receipt.jpg"
    fake_file.write_bytes(b"FAKEJPEG")

    receipt_data = _valid_receipt_json()
    fenced = f"```json\n{json.dumps(receipt_data)}\n```"

    with patch("app.services.llm.get_image_content_blocks") as mock_blocks, \
         patch("app.services.llm._build_client") as mock_client_fn:

        mock_blocks.return_value = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,FAKE"}}]
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_llm_response(fenced)

        result = extract_receipt_data_vision(str(fake_file))

    assert result["total_cents"] == 1130


def test_vision_extraction_returns_empty_on_image_encode_failure(tmp_path):
    fake_file = tmp_path / "receipt.jpg"
    fake_file.write_bytes(b"FAKEJPEG")

    with patch("app.services.llm.get_image_content_blocks", side_effect=Exception("corrupt file")):
        result = extract_receipt_data_vision(str(fake_file))

    assert result == {}


def test_vision_extraction_returns_empty_on_connection_error(tmp_path):
    from openai import APIConnectionError

    fake_file = tmp_path / "receipt.jpg"
    fake_file.write_bytes(b"FAKEJPEG")

    with patch("app.services.llm.get_image_content_blocks") as mock_blocks, \
         patch("app.services.llm._build_client") as mock_client_fn:

        mock_blocks.return_value = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,FAKE"}}]
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())

        result = extract_receipt_data_vision(str(fake_file))

    assert result == {}


def test_vision_extraction_returns_empty_on_invalid_json(tmp_path):
    fake_file = tmp_path / "receipt.jpg"
    fake_file.write_bytes(b"FAKEJPEG")

    with patch("app.services.llm.get_image_content_blocks") as mock_blocks, \
         patch("app.services.llm._build_client") as mock_client_fn:

        mock_blocks.return_value = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,FAKE"}}]
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_llm_response("not valid json {{")

        result = extract_receipt_data_vision(str(fake_file))

    assert result == {}


def test_vision_extraction_retries_without_json_mode_on_status_error(tmp_path):
    from openai import APIStatusError

    fake_file = tmp_path / "receipt.jpg"
    fake_file.write_bytes(b"FAKEJPEG")

    receipt_data = _valid_receipt_json()

    with patch("app.services.llm.get_image_content_blocks") as mock_blocks, \
         patch("app.services.llm._build_client") as mock_client_fn:

        mock_blocks.return_value = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,FAKE"}}]
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client

        # First call (JSON mode) raises APIStatusError; second (plain) succeeds
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_client.chat.completions.create.side_effect = [
            APIStatusError("unsupported", response=mock_response, body={}),
            _make_llm_response(json.dumps(receipt_data)),
        ]

        result = extract_receipt_data_vision(str(fake_file))

    assert result["total_cents"] == 1130
    assert mock_client.chat.completions.create.call_count == 2


def test_vision_extraction_passes_known_entities(tmp_path):
    fake_file = tmp_path / "receipt.jpg"
    fake_file.write_bytes(b"FAKEJPEG")

    receipt_data = _valid_receipt_json()

    with patch("app.services.llm.get_image_content_blocks") as mock_blocks, \
         patch("app.services.llm._build_client") as mock_client_fn:

        mock_blocks.return_value = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,FAKE"}}]
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_llm_response(json.dumps(receipt_data))

        extract_receipt_data_vision(
            str(fake_file),
            known_stores=["Walmart"],
            known_products=["Organic Banana"],
        )

    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    text_part = next(p for p in user_msg["content"] if p["type"] == "text")
    assert "Walmart" in text_part["text"]
    assert "Organic Banana" in text_part["text"]
