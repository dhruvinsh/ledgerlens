import asyncio
import shutil
from pathlib import Path

from PIL import Image

from app.core.config import settings

ALLOWED_RECEIPT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".pdf"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PRODUCT_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def _get_data_dir() -> Path:
    return Path(settings.DATA_DIR).resolve()


def _validate_path(path: Path) -> Path:
    """Ensure path is under DATA_DIR to prevent traversal."""
    resolved = path.resolve()
    resolved.relative_to(_get_data_dir())
    return resolved


async def save_receipt_file(
    file_content: bytes,
    filename: str,
    user_id: str,
    receipt_id: str,
) -> tuple[str, str | None, int]:
    """Save receipt file and return (relative_path, thumbnail_path, page_count)."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_RECEIPT_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    receipt_dir = _get_data_dir() / "receipts" / user_id / receipt_id
    receipt_dir.mkdir(parents=True, exist_ok=True)

    file_path = receipt_dir / f"original{ext}"
    _validate_path(file_path)
    file_path.write_bytes(file_content)

    relative = str(file_path.relative_to(_get_data_dir()))
    thumbnail_rel = None
    page_count = 1

    if ext == ".pdf":
        page_count, thumbnail_rel = await _process_pdf(
            file_path, receipt_dir
        )
    else:
        thumbnail_rel = relative  # For images, the original is the thumbnail

    return relative, thumbnail_rel, page_count


async def _process_pdf(pdf_path: Path, output_dir: Path) -> tuple[int, str | None]:
    """Extract page count and generate first-page thumbnail from PDF."""

    def _do() -> tuple[int, str | None]:
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(pdf_path))
            count = len(doc)
            if count > 0:
                page = doc[0]
                pix = page.get_pixmap(dpi=150)
                thumb_path = output_dir / "thumbnail.png"
                pix.save(str(thumb_path))
                doc.close()
                return count, str(
                    thumb_path.relative_to(_get_data_dir())
                )
            doc.close()
            return count, None
        except Exception:
            return 1, None

    return await asyncio.to_thread(_do)


async def save_product_image(
    file_content: bytes,
    filename: str,
    item_id: str,
) -> str:
    """Save and resize product image to 512x512 WebP. Returns relative path."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image type: {ext}")

    if len(file_content) > MAX_PRODUCT_IMAGE_SIZE:
        raise ValueError("Image exceeds 5 MB limit")

    item_dir = _get_data_dir() / "products" / item_id
    item_dir.mkdir(parents=True, exist_ok=True)

    output_path = item_dir / "image.webp"
    _validate_path(output_path)

    def _resize() -> None:
        img = Image.open(file_content if isinstance(file_content, Path) else __import__("io").BytesIO(file_content))
        img = img.convert("RGB")
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        img.save(str(output_path), "WEBP", quality=85)

    await asyncio.to_thread(_resize)
    return str(output_path.relative_to(_get_data_dir()))


def delete_receipt_files(user_id: str, receipt_id: str) -> None:
    """Delete all files for a receipt."""
    receipt_dir = _get_data_dir() / "receipts" / user_id / receipt_id
    if receipt_dir.exists():
        shutil.rmtree(receipt_dir)


def delete_product_image(item_id: str) -> None:
    """Delete product image directory."""
    item_dir = _get_data_dir() / "products" / item_id
    if item_dir.exists():
        shutil.rmtree(item_dir)


def get_receipt_path(relative_path: str) -> Path:
    """Resolve and validate a receipt file path."""
    full_path = _get_data_dir() / relative_path
    return _validate_path(full_path)
