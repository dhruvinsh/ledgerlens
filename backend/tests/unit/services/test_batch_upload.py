from app.services.receipt import _validate_magic_bytes


# ── Magic byte detection ──


def test_detect_pdf():
    content = b"\x25\x50\x44\x46-1.7 rest of pdf"
    assert _validate_magic_bytes(content) == "application/pdf"


def test_detect_jpeg():
    content = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    assert _validate_magic_bytes(content) == "image/jpeg"


def test_detect_jpeg_exif():
    content = b"\xff\xd8\xff\xe1 Exif data"
    assert _validate_magic_bytes(content) == "image/jpeg"


def test_detect_png():
    content = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a rest"
    assert _validate_magic_bytes(content) == "image/png"


def test_reject_exe():
    content = b"MZ\x90\x00 PE executable"
    assert _validate_magic_bytes(content) is None


def test_reject_zip():
    content = b"PK\x03\x04 zip archive"
    assert _validate_magic_bytes(content) is None


def test_reject_empty():
    assert _validate_magic_bytes(b"") is None


def test_reject_short_bytes():
    assert _validate_magic_bytes(b"\xff\xd8") is None


def test_reject_text():
    assert _validate_magic_bytes(b"Hello, this is a text file") is None
