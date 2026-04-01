import asyncio
import shutil
import tempfile
from pathlib import Path

import pytesseract
from PIL import Image

from app.core.config import settings


def verify_tesseract() -> None:
    """Check that Tesseract binary is available."""
    if not shutil.which("tesseract"):
        raise RuntimeError("Tesseract OCR binary not found on PATH")


def _preprocess_image(img: Image.Image) -> Image.Image:
    """Grayscale → upscale if small → binarize."""
    img = img.convert("L")
    if img.width < 1500:
        scale = 1500 / img.width
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.Resampling.LANCZOS,
        )
    return img.point(lambda x: 255 if x > 150 else 0, mode="1")


def _ocr_image(image_path: str) -> tuple[str, float]:
    """Run Tesseract on a single image. Returns (text, confidence 0.0–1.0)."""
    img = Image.open(image_path)
    processed = _preprocess_image(img)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        processed.save(tmp.name)
        tmp_path = tmp.name

    try:
        data = pytesseract.image_to_data(
            tmp_path,
            lang=settings.TESSERACT_LANG,
            config=f"--oem 3 --psm {settings.TESSERACT_PSM} --dpi {settings.TESSERACT_DPI}",
            output_type=pytesseract.Output.DICT,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # Build lines from word-level data
    lines: dict[int, list[str]] = {}
    confidences: list[float] = []

    for i, text in enumerate(data["text"]):
        text = text.strip()
        if not text:
            continue
        line_num = data["line_num"][i]
        lines.setdefault(line_num, []).append(text)
        conf = data["conf"][i]
        if isinstance(conf, (int, float)) and conf >= 0:
            confidences.append(float(conf))

    full_text = "\n".join(" ".join(words) for words in lines.values())
    avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0

    return full_text, avg_conf


def _ocr_pdf(pdf_path: str) -> tuple[str, float, int]:
    """OCR all pages of a PDF. Returns (text, avg_confidence, page_count)."""
    import fitz

    doc = fitz.open(pdf_path)
    page_count = len(doc)
    all_texts: list[str] = []
    all_confs: list[float] = []

    for page in doc:
        pix = page.get_pixmap(dpi=settings.TESSERACT_DPI)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            pix.save(tmp.name)
            tmp_path = tmp.name

        try:
            text, conf = _ocr_image(tmp_path)
            all_texts.append(text)
            all_confs.append(conf)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    doc.close()

    full_text = "\n\n".join(all_texts)
    avg_conf = (sum(all_confs) / len(all_confs)) if all_confs else 0.0

    return full_text, avg_conf, page_count


async def extract_text(file_path: str) -> tuple[str, float]:
    """Extract text from an image file. Runs in a thread."""
    return await asyncio.to_thread(_ocr_image, file_path)


async def extract_text_from_pdf(file_path: str) -> tuple[str, float, int]:
    """Extract text from a PDF file. Runs in a thread."""
    return await asyncio.to_thread(_ocr_pdf, file_path)
