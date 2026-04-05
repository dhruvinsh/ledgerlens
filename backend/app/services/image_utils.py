import base64
import logging
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)

_MAX_DIMENSION = 2048  # pixels — keeps token costs reasonable


def _resize_if_needed(img: Image.Image) -> Image.Image:
    """Downscale image so its longest side is at most _MAX_DIMENSION."""
    w, h = img.size
    longest = max(w, h)
    if longest <= _MAX_DIMENSION:
        return img
    scale = _MAX_DIMENSION / longest
    new_size = (int(w * scale), int(h * scale))
    return img.resize(new_size, Image.LANCZOS)


def encode_image_to_data_url(image_path: str) -> str:
    """Read an image file and return a data:image/...;base64,... URL.

    Resizes the image if its longest side exceeds 2048px.
    """
    ext = Path(image_path).suffix.lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

    with Image.open(image_path) as img:
        img = _resize_if_needed(img)
        # Ensure compatible mode for JPEG
        if mime == "image/jpeg" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        import io
        buf = io.BytesIO()
        fmt = "JPEG" if mime == "image/jpeg" else "PNG"
        img.save(buf, format=fmt)
        data = base64.b64encode(buf.getvalue()).decode("ascii")

    return f"data:{mime};base64,{data}"


def encode_pdf_pages_to_data_urls(pdf_path: str, dpi: int = 200) -> list[str]:
    """Rasterize each PDF page to PNG and return a list of data URLs."""
    urls: list[str] = []
    doc = fitz.open(pdf_path)
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            data = base64.b64encode(png_bytes).decode("ascii")
            urls.append(f"data:image/png;base64,{data}")
    finally:
        doc.close()
    return urls


def get_image_content_blocks(file_path: str) -> list[dict]:
    """Return OpenAI-format image content blocks for a receipt file.

    For images: returns a single block.
    For PDFs: returns one block per page.

    Logs a warning when multiple pages are produced, since some local vision
    models (e.g. LLaVA on Ollama) only support a single image per request.
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        data_urls = encode_pdf_pages_to_data_urls(file_path)
        if len(data_urls) > 1:
            logger.warning(
                "Sending %d page images for %s — some vision models only support "
                "a single image per request (e.g. LLaVA on Ollama). If extraction "
                "fails, consider a model with multi-image support.",
                len(data_urls),
                file_path,
            )
    else:
        data_urls = [encode_image_to_data_url(file_path)]

    return [
        {"type": "image_url", "image_url": {"url": url}}
        for url in data_urls
    ]
