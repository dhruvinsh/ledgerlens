"""Integration tests for POST /api/v1/receipts/batch."""

import io
from pathlib import Path

import httpx
import pytest

SAMPLES_DIR = Path(__file__).parent.parent.parent.parent / "samples"

# Minimal valid file headers for test fixtures
MINIMAL_PDF = b"%PDF-1.4 fake pdf content for testing"
MINIMAL_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100
MINIMAL_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def _make_file(name: str, content: bytes, content_type: str):
    """Create a tuple suitable for httpx files param."""
    return ("files", (name, io.BytesIO(content), content_type))


# ── Authentication ──


@pytest.mark.asyncio
async def test_batch_upload_requires_auth(client: httpx.AsyncClient):
    resp = await client.post(
        "/api/v1/receipts/batch",
        files=[_make_file("a.pdf", MINIMAL_PDF, "application/pdf")],
        data={"source": "upload"},
    )
    assert resp.status_code == 401


# ── Happy path ──


@pytest.mark.asyncio
async def test_batch_upload_single_file(auth_client: httpx.AsyncClient):
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=[_make_file("receipt.pdf", MINIMAL_PDF, "application/pdf")],
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["receipts"]) == 1
    assert len(data["errors"]) == 0
    assert data["receipts"][0]["status"] == "pending"
    assert data["receipts"][0]["source"] == "upload"


@pytest.mark.asyncio
async def test_batch_upload_multiple_files(auth_client: httpx.AsyncClient):
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=[
            _make_file("a.pdf", MINIMAL_PDF, "application/pdf"),
            _make_file("b.pdf", MINIMAL_PDF, "application/pdf"),
            _make_file("c.pdf", MINIMAL_PDF, "application/pdf"),
        ],
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["receipts"]) == 3
    assert len(data["errors"]) == 0

    # Each receipt should have a unique id
    ids = [r["id"] for r in data["receipts"]]
    assert len(set(ids)) == 3


@pytest.mark.asyncio
async def test_batch_upload_mixed_types(auth_client: httpx.AsyncClient):
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=[
            _make_file("receipt.pdf", MINIMAL_PDF, "application/pdf"),
            _make_file("photo.jpg", MINIMAL_JPEG, "image/jpeg"),
            _make_file("scan.png", MINIMAL_PNG, "image/png"),
        ],
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["receipts"]) == 3
    assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_batch_upload_receipts_appear_in_list(auth_client: httpx.AsyncClient):
    await auth_client.post(
        "/api/v1/receipts/batch",
        files=[
            _make_file("a.pdf", MINIMAL_PDF, "application/pdf"),
            _make_file("b.pdf", MINIMAL_PDF, "application/pdf"),
        ],
        data={"source": "upload"},
    )

    resp = await auth_client.get("/api/v1/receipts")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


# ── Validation: file count ──


@pytest.mark.asyncio
async def test_batch_upload_exceeds_max_files(auth_client: httpx.AsyncClient):
    files = [
        _make_file(f"file_{i}.pdf", MINIMAL_PDF, "application/pdf")
        for i in range(21)
    ]
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=files,
        data={"source": "upload"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_batch_upload_exactly_max_files(auth_client: httpx.AsyncClient):
    files = [
        _make_file(f"file_{i}.pdf", MINIMAL_PDF, "application/pdf")
        for i in range(20)
    ]
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=files,
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["receipts"]) == 20


# ── Validation: content type ──


@pytest.mark.asyncio
async def test_batch_upload_rejects_unsupported_content_type(auth_client: httpx.AsyncClient):
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=[
            _make_file("good.pdf", MINIMAL_PDF, "application/pdf"),
            _make_file("bad.exe", b"MZ\x90\x00 fake exe", "application/octet-stream"),
        ],
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["receipts"]) == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["filename"] == "bad.exe"
    assert "Unsupported file type" in data["errors"][0]["detail"]


# ── Validation: magic bytes ──


@pytest.mark.asyncio
async def test_batch_upload_rejects_spoofed_content_type(auth_client: httpx.AsyncClient):
    """File claims to be PDF via content-type but has EXE magic bytes."""
    exe_content = b"MZ\x90\x00 this is actually an exe"
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=[_make_file("sneaky.pdf", exe_content, "application/pdf")],
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["receipts"]) == 0
    assert len(data["errors"]) == 1
    assert "does not match a supported format" in data["errors"][0]["detail"]


# ── Validation: per-file size ──


@pytest.mark.asyncio
async def test_batch_upload_rejects_oversized_file(auth_client: httpx.AsyncClient):
    # 11 MB file with valid PDF magic bytes
    large_pdf = b"%PDF-1.4 " + b"\x00" * (11 * 1024 * 1024)
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=[
            _make_file("small.pdf", MINIMAL_PDF, "application/pdf"),
            _make_file("huge.pdf", large_pdf, "application/pdf"),
        ],
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["receipts"]) == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["filename"] == "huge.pdf"
    assert "10MB" in data["errors"][0]["detail"]


# ── Validation: aggregate size ──


@pytest.mark.asyncio
async def test_batch_upload_rejects_on_aggregate_size(auth_client: httpx.AsyncClient):
    # Each file is 9 MB (under per-file limit), but 6 of them exceed 50 MB aggregate
    chunk = b"%PDF-1.4 " + b"\x00" * (9 * 1024 * 1024)
    files = [
        _make_file(f"big_{i}.pdf", chunk, "application/pdf")
        for i in range(6)
    ]
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=files,
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()

    # First 5 fit within 50 MB (5 * ~9MB = ~45MB), 6th pushes over
    assert len(data["receipts"]) == 5
    assert len(data["errors"]) == 1
    assert "Batch size limit" in data["errors"][0]["detail"]


# ── Partial success ──


@pytest.mark.asyncio
async def test_batch_upload_partial_success(auth_client: httpx.AsyncClient):
    """Mix of valid and invalid files returns both receipts and errors."""
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=[
            _make_file("good1.pdf", MINIMAL_PDF, "application/pdf"),
            _make_file("bad.txt", b"plain text", "text/plain"),
            _make_file("good2.png", MINIMAL_PNG, "image/png"),
            _make_file("fake.pdf", b"not actually pdf", "application/pdf"),
        ],
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["receipts"]) == 2
    assert len(data["errors"]) == 2

    error_filenames = {e["filename"] for e in data["errors"]}
    assert "bad.txt" in error_filenames
    assert "fake.pdf" in error_filenames


@pytest.mark.asyncio
async def test_batch_upload_all_invalid(auth_client: httpx.AsyncClient):
    """When every file fails validation, receipts is empty but errors are populated."""
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=[
            _make_file("a.exe", b"MZ\x90\x00", "application/octet-stream"),
            _make_file("b.txt", b"hello world", "text/plain"),
        ],
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["receipts"]) == 0
    assert len(data["errors"]) == 2


# ── Response shape ──


@pytest.mark.asyncio
async def test_batch_upload_response_shape(auth_client: httpx.AsyncClient):
    """Verify the response contains all expected fields."""
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=[_make_file("test.pdf", MINIMAL_PDF, "application/pdf")],
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()

    assert "receipts" in data
    assert "errors" in data

    receipt = data["receipts"][0]
    assert "id" in receipt
    assert "user_id" in receipt
    assert "status" in receipt
    assert "source" in receipt
    assert "created_at" in receipt
    assert "page_count" in receipt


# ── Edge cases ──


@pytest.mark.asyncio
async def test_batch_upload_empty_files_list(auth_client: httpx.AsyncClient):
    """Sending no files should fail with a validation error."""
    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        data={"source": "upload"},
    )
    assert resp.status_code == 422


# ── With real sample PDFs (skipped if samples not available) ──


@pytest.mark.asyncio
async def test_batch_upload_real_pdfs(auth_client: httpx.AsyncClient):
    pdf_path = SAMPLES_DIR / "527590516490408.pdf"
    if not pdf_path.exists():
        pytest.skip("Sample PDF not found")

    with open(pdf_path, "rb") as f:
        content = f.read()

    resp = await auth_client.post(
        "/api/v1/receipts/batch",
        files=[
            _make_file("receipt1.pdf", content, "application/pdf"),
            _make_file("receipt2.pdf", content, "application/pdf"),
        ],
        data={"source": "upload"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["receipts"]) == 2
    for receipt in data["receipts"]:
        assert receipt["status"] == "pending"
        assert receipt["thumbnail_path"] is not None
        assert receipt["page_count"] >= 1
