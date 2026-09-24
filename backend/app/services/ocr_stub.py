"""Screenshot intake. OCR is not implemented in Phase 1; this is the single swap point for it.

The image is validated by its magic bytes (the declared MIME type is only a
claim) and never logged or stored by this app. The multipart parser may spool
uploads over 1 MB to an OS temporary file; FastAPI closes the upload after every
request (success or error), which deletes that file.
"""

from typing import Literal

ImageKind = Literal["png", "jpeg", "webp"]


class UnsupportedImageError(ValueError):
    pass


def sniff_image_kind(data: bytes) -> ImageKind:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    raise UnsupportedImageError("only PNG, JPEG, or WebP screenshots are accepted")


def extract_text_stub(image_bytes: bytes, declared_mime_type: str | None) -> str:
    sniff_image_kind(image_bytes)
    return ""
