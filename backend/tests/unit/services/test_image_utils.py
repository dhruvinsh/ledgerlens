"""Unit tests for image_utils — base64 encoding helpers for vision LLM."""
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.services.image_utils import (
    _MAX_DIMENSION,
    _resize_if_needed,
    encode_image_to_data_url,
    get_image_content_blocks,
)


# ── _resize_if_needed ────────────────────────────────────────────────────────


def test_resize_not_needed_small_image():
    img = Image.new("RGB", (800, 600))
    result = _resize_if_needed(img)
    assert result.size == (800, 600)


def test_resize_wide_image():
    img = Image.new("RGB", (4096, 1000))
    result = _resize_if_needed(img)
    assert result.width == _MAX_DIMENSION
    assert result.height == pytest.approx(1000 * _MAX_DIMENSION / 4096, abs=1)


def test_resize_tall_image():
    img = Image.new("RGB", (1000, 4096))
    result = _resize_if_needed(img)
    assert result.height == _MAX_DIMENSION
    assert result.width == pytest.approx(1000 * _MAX_DIMENSION / 4096, abs=1)


def test_resize_exactly_at_limit():
    img = Image.new("RGB", (_MAX_DIMENSION, _MAX_DIMENSION))
    result = _resize_if_needed(img)
    assert result.size == (_MAX_DIMENSION, _MAX_DIMENSION)


# ── encode_image_to_data_url ──────────────────────────────────────────────────


def _make_tmp_image(tmp_path: Path, ext: str, size=(100, 100)) -> Path:
    path = tmp_path / f"receipt{ext}"
    img = Image.new("RGB", size, color=(200, 150, 100))
    img.save(path)
    return path


def test_encode_jpeg_returns_data_url(tmp_path):
    path = _make_tmp_image(tmp_path, ".jpg")
    url = encode_image_to_data_url(str(path))
    assert url.startswith("data:image/jpeg;base64,")
    assert len(url) > 50


def test_encode_png_returns_data_url(tmp_path):
    path = _make_tmp_image(tmp_path, ".png")
    url = encode_image_to_data_url(str(path))
    assert url.startswith("data:image/png;base64,")


def test_encode_large_image_is_resized(tmp_path):
    # Create image larger than _MAX_DIMENSION
    path = _make_tmp_image(tmp_path, ".jpg", size=(4096, 3072))
    url = encode_image_to_data_url(str(path))
    # Decode and verify dimensions were reduced
    import base64
    data = url.split(",", 1)[1]
    img = Image.open(io.BytesIO(base64.b64decode(data)))
    assert max(img.size) <= _MAX_DIMENSION


# ── get_image_content_blocks ──────────────────────────────────────────────────


def test_get_image_content_blocks_single_image(tmp_path):
    path = _make_tmp_image(tmp_path, ".jpg")
    blocks = get_image_content_blocks(str(path))
    assert len(blocks) == 1
    assert blocks[0]["type"] == "image_url"
    assert "image_url" in blocks[0]
    assert blocks[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_get_image_content_blocks_png(tmp_path):
    path = _make_tmp_image(tmp_path, ".png")
    blocks = get_image_content_blocks(str(path))
    assert len(blocks) == 1
    assert blocks[0]["image_url"]["url"].startswith("data:image/png;base64,")


def test_get_image_content_blocks_pdf_multi_page(tmp_path):
    """Each PDF page should produce one content block."""
    fake_page = MagicMock()
    fake_page.get_pixmap.return_value = MagicMock(tobytes=lambda fmt: b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    fake_doc = MagicMock()
    fake_doc.__len__ = lambda self: 3
    fake_doc.__getitem__ = lambda self, i: fake_page

    pdf_path = tmp_path / "receipt.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with patch("app.services.image_utils.fitz.open", return_value=fake_doc):
        with patch("app.services.image_utils.base64.b64encode", return_value=b"FAKEBASE64"):
            blocks = get_image_content_blocks(str(pdf_path))

    assert len(blocks) == 3
    for block in blocks:
        assert block["type"] == "image_url"
        assert "image_url" in block


def test_get_image_content_blocks_pdf_warns_multi_page(tmp_path, caplog):
    """Multiple PDF pages should log a warning about model compatibility."""
    import logging
    fake_page = MagicMock()
    fake_page.get_pixmap.return_value = MagicMock(tobytes=lambda fmt: b"\x89PNG" + b"\x00" * 50)

    fake_doc = MagicMock()
    fake_doc.__len__ = lambda self: 2
    fake_doc.__getitem__ = lambda self, i: fake_page

    pdf_path = tmp_path / "receipt.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with patch("app.services.image_utils.fitz.open", return_value=fake_doc):
        with patch("app.services.image_utils.base64.b64encode", return_value=b"FAKEBASE64"):
            with caplog.at_level(logging.WARNING, logger="app.services.image_utils"):
                get_image_content_blocks(str(pdf_path))

    assert any("single image" in r.message.lower() or "llava" in r.message.lower() for r in caplog.records)
