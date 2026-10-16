"""File operations for PDF Toolkit.

Every public function here is UI-agnostic: it takes paths and options, reports
progress through an optional callback, and returns plain dicts that can be sent
straight to the front end as JSON.
"""

from __future__ import annotations

import io
import os
import re
import shutil
from pathlib import Path
from typing import Callable, Iterable

import pymupdf
from PIL import Image, ImageOps

PDF_EXTS = {".pdf"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# Progress callback: (fraction 0..1, message). Cancel check: returns True to stop.
Progress = Callable[[float, str], None]
Cancelled = Callable[[], bool]

PDF_LEVELS = {
    # name: (only touch images above this dpi, downsample them to this dpi, jpeg quality)
    "light": (200, 150, 80),
    "recommended": (140, 120, 65),
    "extreme": (96, 72, 45),
}

PAGE_SIZES = {
    "a4": (595.28, 841.89),
    "letter": (612.0, 792.0),
}


class OperationCancelled(Exception):
    pass


def _noop_progress(_fraction: float, _message: str) -> None:
    pass


def _never_cancelled() -> bool:
    return False


def _check(cancelled: Cancelled) -> None:
    if cancelled():
        raise OperationCancelled()


def unique_path(path: str | Path) -> Path:
    """Return `path`, or `name (1).ext`, `name (2).ext`, ... if it already exists."""
    path = Path(path)
    if not path.exists():
        return path
    for i in range(1, 10_000):
        candidate = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find a free file name for {path}")


def _out_dir(src: Path, out_dir: str | None) -> Path:
    target = Path(out_dir) if out_dir else src.parent
    target.mkdir(parents=True, exist_ok=True)
    return target


def _result(src, out, ok=True, error=None, **extra) -> dict:
    data = {
        "source": str(src) if src else None,
        "output": str(out) if out else None,
        "ok": ok,
        "error": error,
    }
    if ok and src and out and Path(src).is_file() and Path(out).is_file():
        data["before"] = Path(src).stat().st_size
        data["after"] = Path(out).stat().st_size
    data.update(extra)
    return data


def _open_pdf(path: Path) -> pymupdf.Document:
    doc = pymupdf.open(path)
    if doc.needs_pass:
        doc.close()
        raise ValueError("PDF is password protected")
    if not doc.is_pdf:
        doc.close()
        raise ValueError("Not a PDF file")
    return doc


# --------------------------------------------------------------------------- #
# Compress PDF
# --------------------------------------------------------------------------- #

def compress_pdf(
    src: str,
    out_dir: str | None = None,
    level: str = "recommended",
    grayscale: bool = False,
) -> dict:
    src_path = Path(src)
    threshold, target, quality = PDF_LEVELS[level]
    out = unique_path(_out_dir(src_path, out_dir) / f"{src_path.stem}_compressed.pdf")

    doc = _open_pdf(src_path)
    try:
        doc.rewrite_images(
            dpi_threshold=threshold,
            dpi_target=target,
            quality=quality,
            set_to_gray=grayscale,
        )
        try:
            doc.subset_fonts()
        except Exception:
            pass  # font subsetting is a bonus; never fail the whole job over it
        doc.ez_save(out, garbage=4, clean=True, deflate=True, use_objstms=1)
    finally:
        doc.close()

    if out.stat().st_size >= src_path.stat().st_size:
        # Nothing to gain: hand back an identical copy rather than a bigger file.
        shutil.copyfile(src_path, out)
        return _result(src_path, out, note="Already optimized; kept original quality")
    return _result(src_path, out)


# --------------------------------------------------------------------------- #
# Compress images
# --------------------------------------------------------------------------- #

_FORMAT_EXT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def _pick_format(img: Image.Image, src_ext: str, requested: str) -> str:
    if requested in ("jpg", "jpeg"):
        return "JPEG"
    if requested == "webp":
        return "WEBP"
    if requested == "png":
        return "PNG"
    # "keep": stay in the source format where it's a sensible web format.
    if src_ext in (".jpg", ".jpeg"):
        return "JPEG"
    if src_ext == ".png":
        return "PNG"
    if src_ext == ".webp":
        return "WEBP"
    return "PNG" if _has_alpha(img) else "JPEG"


def _has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)


def _flatten(img: Image.Image) -> Image.Image:
    """Composite any transparency onto white and return an RGB image."""
    if _has_alpha(img):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return img.convert("RGB")


def _encode_image(img: Image.Image, fmt: str, quality: int, icc: bytes | None) -> bytes:
    buf = io.BytesIO()
    extra = {"icc_profile": icc} if icc else {}
    if fmt == "JPEG":
        _flatten(img).save(buf, "JPEG", quality=quality, optimize=True, progressive=True, **extra)
    elif fmt == "WEBP":
        mode = "RGBA" if _has_alpha(img) else "RGB"
        img.convert(mode).save(buf, "WEBP", quality=quality, method=6, **extra)
    else:  # PNG
        if quality < 90:
            # Lossy PNG: reduce to a 256-colour palette, which typically halves the size.
            if _has_alpha(img):
                img = img.convert("RGBA").quantize(256, method=Image.Quantize.FASTOCTREE)
            else:
                img = img.convert("RGB").quantize(256, method=Image.Quantize.MEDIANCUT)
        img.save(buf, "PNG", optimize=True, **extra)
    return buf.getvalue()


def compress_image(
    src: str,
    out_dir: str | None = None,
    quality: int = 75,
    max_dim: int = 0,
    fmt: str = "keep",
) -> dict:
    src_path = Path(src)
    quality = max(1, min(95, int(quality)))

    with Image.open(src_path) as opened:
        opened.load()
        icc = opened.info.get("icc_profile")
        img = ImageOps.exif_transpose(opened)
    resized = False
    if max_dim and max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        resized = True

    out_format = _pick_format(img, src_path.suffix.lower(), fmt)
    data = _encode_image(img, out_format, quality, icc)
    ext = _FORMAT_EXT[out_format]
    out = unique_path(_out_dir(src_path, out_dir) / f"{src_path.stem}_compressed{ext}")

    same_format = ext == src_path.suffix.lower() or (
        ext == ".jpg" and src_path.suffix.lower() == ".jpeg"
    )
    if same_format and not resized and len(data) >= src_path.stat().st_size:
        shutil.copyfile(src_path, out)
        return _result(src_path, out, note="Already optimized; kept original")

    out.write_bytes(data)
    return _result(src_path, out)


# --------------------------------------------------------------------------- #
# Merge PDFs
# --------------------------------------------------------------------------- #

def merge_pdfs(
    paths: list[str],
    out_path: str,
    progress: Progress = _noop_progress,
    cancelled: Cancelled = _never_cancelled,
) -> dict:
    if len(paths) < 2:
        raise ValueError("Pick at least two PDFs to merge")
    out = Path(out_path)
    merged = pymupdf.open()
    try:
        for i, p in enumerate(paths):
            _check(cancelled)
            progress(i / len(paths), f"Adding {Path(p).name}")
            src = _open_pdf(Path(p))
            try:
                merged.insert_pdf(src)
            finally:
                src.close()
        progress(0.95, "Saving")
        out.parent.mkdir(parents=True, exist_ok=True)
        merged.save(out, garbage=3, deflate=True)
        pages = merged.page_count
    finally:
        merged.close()
    return _result(None, out, pages=pages, after=out.stat().st_size,
                   before=sum(Path(p).stat().st_size for p in paths))


# --------------------------------------------------------------------------- #
# Images to PDF
# --------------------------------------------------------------------------- #

def _image_stream(path: Path) -> tuple[bytes, int, int]:
    """Bytes PyMuPDF can embed, plus the upright pixel size.

    JPEG and PNG files are embedded as-is (no quality loss) unless they carry an
    EXIF rotation, in which case they are re-encoded upright.
    """
    with Image.open(path) as img:
        img.load()
        orientation = img.getexif().get(0x0112, 1)
        fmt = img.format
        if fmt in ("JPEG", "PNG") and orientation == 1:
            return path.read_bytes(), img.width, img.height
        upright = ImageOps.exif_transpose(img)
        buf = io.BytesIO()
        if fmt == "JPEG" or not _has_alpha(upright):
            _flatten(upright).save(buf, "JPEG", quality=95)
        else:
            upright.save(buf, "PNG")
        return buf.getvalue(), upright.width, upright.height


def images_to_pdf(
    paths: list[str],
    out_path: str,
    page_size: str = "fit",
    orientation: str = "auto",
    margin: float = 0,
    progress: Progress = _noop_progress,
    cancelled: Cancelled = _never_cancelled,
) -> dict:
    if not paths:
        raise ValueError("Pick at least one image")
    out = Path(out_path)
    doc = pymupdf.open()
    try:
        for i, p in enumerate(paths):
            _check(cancelled)
            progress(i / len(paths), f"Adding {Path(p).name}")
            data, w_px, h_px = _image_stream(Path(p))
            # Treat pixels as 96 dpi for "fit" pages, matching how screens show them.
            img_w, img_h = w_px * 0.75, h_px * 0.75

            if page_size == "fit":
                page_w, page_h = img_w + 2 * margin, img_h + 2 * margin
            else:
                page_w, page_h = PAGE_SIZES[page_size]
                landscape = (
                    orientation == "landscape"
                    or (orientation == "auto" and w_px > h_px)
                )
                if landscape:
                    page_w, page_h = page_h, page_w

            page = doc.new_page(width=page_w, height=page_h)
            box = pymupdf.Rect(margin, margin, page_w - margin, page_h - margin)
            page.insert_image(box, stream=data, keep_proportion=True)
        progress(0.95, "Saving")
        out.parent.mkdir(parents=True, exist_ok=True)
        doc.save(out, garbage=3, deflate=True)
        pages = doc.page_count
    finally:
        doc.close()
    return _result(None, out, pages=pages, after=out.stat().st_size,
                   before=sum(Path(p).stat().st_size for p in paths))


# --------------------------------------------------------------------------- #
# PDF to images
# --------------------------------------------------------------------------- #

def parse_page_spec(spec: str, page_count: int) -> list[int]:
    """Turn "1-3, 5, 8-" into zero-based page indexes. Empty means every page."""
    spec = (spec or "").strip()
    if not spec:
        return list(range(page_count))
    pages: list[int] = []
    for part in re.split(r"[,\s]+", spec):
        if not part:
            continue
        m = re.fullmatch(r"(\d*)\s*-\s*(\d*)|(\d+)", part)
        if not m:
            raise ValueError(f"Can't understand page range '{part}'")
        if m.group(3):
            start = end = int(m.group(3))
        else:
            start = int(m.group(1)) if m.group(1) else 1
            end = int(m.group(2)) if m.group(2) else page_count
        if start < 1 or end < start:
            raise ValueError(f"Invalid page range '{part}'")
        for n in range(start, min(end, page_count) + 1):
            if n - 1 not in pages:
                pages.append(n - 1)
    if not pages:
        raise ValueError(f"No pages in range '{spec}' (document has {page_count})")
    return pages


def pdf_to_images(
    src: str,
    out_dir: str | None = None,
    fmt: str = "png",
    dpi: int = 150,
    pages: str = "",
    progress: Progress = _noop_progress,
    cancelled: Cancelled = _never_cancelled,
) -> dict:
    src_path = Path(src)
    ext = ".jpg" if fmt in ("jpg", "jpeg") else ".png"
    folder = unique_path(_out_dir(src_path, out_dir) / f"{src_path.stem}_pages")

    doc = _open_pdf(src_path)
    try:
        indexes = parse_page_spec(pages, doc.page_count)
        folder.mkdir(parents=True)
        width = max(3, len(str(doc.page_count)))
        written = 0
        for n, idx in enumerate(indexes):
            _check(cancelled)
            progress(n / len(indexes), f"Page {idx + 1} of {doc.page_count}")
            pix = doc[idx].get_pixmap(dpi=int(dpi), alpha=False)
            target = folder / f"{src_path.stem}_page_{idx + 1:0{width}d}{ext}"
            if ext == ".jpg":
                pix.save(target, jpg_quality=90)
            else:
                pix.save(target)
            written += 1
    finally:
        doc.close()
    total = sum(f.stat().st_size for f in folder.iterdir())
    return _result(src_path, folder, pages=written, after=total,
                   before=src_path.stat().st_size)


# --------------------------------------------------------------------------- #
# Helpers for the UI
# --------------------------------------------------------------------------- #

def expand_paths(paths: Iterable[str]) -> list[str]:
    """Expand dropped folders into the supported files they contain."""
    out: list[str] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for child in sorted(path.rglob("*"), key=lambda c: str(c).lower()):
                if child.is_file() and child.suffix.lower() in PDF_EXTS | IMAGE_EXTS:
                    out.append(str(child))
        elif path.is_file():
            out.append(str(path))
    return out


def file_kind(path: str) -> str | None:
    ext = os.path.splitext(path)[1].lower()
    if ext in PDF_EXTS:
        return "pdf"
    if ext in IMAGE_EXTS:
        return "image"
    return None


def thumbnail_png(path: str, size: int = 160) -> tuple[bytes | None, int | None]:
    """Small PNG preview of an image or a PDF's first page, plus page count for PDFs."""
    kind = file_kind(path)
    try:
        if kind == "pdf":
            doc = pymupdf.open(path)
            try:
                if doc.needs_pass:
                    return None, None
                count = doc.page_count
                page = doc[0]
                zoom = size / max(page.rect.width, page.rect.height)
                pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
                return pix.tobytes("png"), count
            finally:
                doc.close()
        if kind == "image":
            with Image.open(path) as img:
                img.draft("RGB", (size * 2, size * 2))  # fast path for big JPEGs
                img = ImageOps.exif_transpose(img)
                img.thumbnail((size, size))
                buf = io.BytesIO()
                _flatten(img).save(buf, "PNG")
                return buf.getvalue(), None
    except Exception:
        pass
    return None, None
