"""Helpers to resolve and manage product image paths safely (no path traversal)."""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings

ALLOWED_UPLOAD_SUFFIXES = {'.png'}
# Legacy static assets (e.g. SVG) still listed on the storefront.
ALLOWED_DISPLAY_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'}
ALLOWED_IMAGE_SUFFIXES = ALLOWED_DISPLAY_SUFFIXES  # alias for listing/delete
_SAFE_SLUG = re.compile(r'^[a-z0-9\-]+$')
_SAFE_FILENAME = re.compile(r'^[a-zA-Z0-9._\-]+$')
# Marks media/produtos/<slug>/ as the storefront source even when empty,
# so removing the last image does not fall back to static files.
_GALLERY_MARKER = '.galeria'


def _slug_ok(slug: str) -> bool:
    return bool(slug and _SAFE_SLUG.match(slug))


def produto_images_base() -> Path:
    return (settings.BASE_DIR / 'static' / 'images' / 'produtos').resolve()


def produto_media_base() -> Path:
    return (Path(settings.MEDIA_ROOT) / 'produtos').resolve()


def _safe_subdir(base: Path, slug: str) -> Path | None:
    if not _slug_ok(slug):
        return None
    target = (base / slug).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return None
    return target


def _list_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in ALLOWED_IMAGE_SUFFIXES
    )


def _numbered_name(index: int, suffix: str) -> str:
    return f'{index + 1:02d}{suffix.lower()}'


def _marker_path(media_dir: Path) -> Path:
    return media_dir / _GALLERY_MARKER


def _touch_marker(media_dir: Path) -> None:
    _marker_path(media_dir).write_text('1', encoding='ascii')


def _media_is_source(media_dir: Path | None) -> bool:
    if media_dir is None or not media_dir.is_dir():
        return False
    return bool(_list_files(media_dir)) or _marker_path(media_dir).is_file()


def _gallery_paths(slug: str) -> tuple[list[Path], str]:
    """Files currently shown on the store, plus 'media' or 'static'."""
    media_dir = _safe_subdir(produto_media_base(), slug)
    if _media_is_source(media_dir):
        return _list_files(media_dir), 'media'

    static_dir = _safe_subdir(produto_images_base(), slug)
    if static_dir is None:
        return [], 'static'
    return _list_files(static_dir), 'static'


def _public_url(slug: str, path: Path, source: str) -> str:
    mtime = int(path.stat().st_mtime)
    if source == 'media':
        base = settings.MEDIA_URL.rstrip('/')
        return f'{base}/produtos/{slug}/{path.name}?v={mtime}'
    base = settings.STATIC_URL.rstrip('/')
    return f'{base}/images/produtos/{slug}/{path.name}?v={mtime}'


def list_produto_gallery(slug: str) -> list[dict]:
    """Storefront order as {index, name, url, source}."""
    files, source = _gallery_paths(slug)
    return [
        {
            'index': index,
            'name': path.name,
            'url': _public_url(slug, path, source),
            'source': source,
        }
        for index, path in enumerate(files)
    ]


def list_produto_images(slug: str) -> list[str]:
    """
    Return absolute URL paths for product images.
    Prefers media/produtos/<slug>/; falls back to static/images/produtos/<slug>/.
    """
    return [item['url'] for item in list_produto_gallery(slug)]


def first_produto_image(slug: str) -> str | None:
    images = list_produto_images(slug)
    return images[0] if images else None


def list_produto_media_images(slug: str) -> list[dict]:
    """Return media images as {name, url}, in storefront order."""
    return [
        {'name': item['name'], 'url': item['url']}
        for item in list_produto_gallery(slug)
        if item['source'] == 'media'
    ]


def _max_bytes() -> int:
    return getattr(settings, 'MAX_PRODUTO_IMAGE_BYTES', 5 * 1024 * 1024)


def _read_upload(uploaded) -> tuple[bytes, str] | None:
    if not uploaded:
        return None
    name = getattr(uploaded, 'name', '') or ''
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        return None
    size = getattr(uploaded, 'size', None)
    if size is not None and size > _max_bytes():
        return None
    data = b''.join(uploaded.chunks())
    if len(data) > _max_bytes():
        return None
    return data, suffix


def _ensure_media_dir(slug: str) -> Path | None:
    media_dir = _safe_subdir(produto_media_base(), slug)
    if media_dir is None:
        return None
    media_dir.mkdir(parents=True, exist_ok=True)
    return media_dir


def _is_numbered(files: list[Path]) -> bool:
    expected = [_numbered_name(index, path.suffix) for index, path in enumerate(files)]
    return [path.name for path in files] == expected


def _clear_images(media_dir: Path) -> None:
    for path in _list_files(media_dir):
        path.unlink()


def materialize_produto_gallery(slug: str) -> list[Path]:
    """
    Copy the gallery the store shows into media/produtos/<slug>/ as 01.ext, 02.ext, ...
    Existing numbered media files are left in place. Static originals are not deleted.
    """
    media_dir = _ensure_media_dir(slug)
    if media_dir is None:
        return []

    files, source = _gallery_paths(slug)
    if source == 'media' and _is_numbered(files):
        _touch_marker(media_dir)
        return files

    blobs = [
        (_numbered_name(index, path.suffix), path.read_bytes())
        for index, path in enumerate(files)
    ]
    _clear_images(media_dir)
    written: list[Path] = []
    for name, data in blobs:
        dest = media_dir / name
        dest.write_bytes(data)
        written.append(dest)
    _touch_marker(media_dir)
    return written


def replace_produto_image(slug: str, index: int, uploaded) -> bool:
    """Overwrite storefront slot `index` (0 = first image) with a PNG upload."""
    parsed = _read_upload(uploaded)
    if parsed is None:
        return False
    data, suffix = parsed
    files = materialize_produto_gallery(slug)
    if index < 0 or index >= len(files):
        return False
    media_dir = files[index].parent
    old = files[index]
    dest = media_dir / _numbered_name(index, suffix)
    if old.resolve() != dest.resolve() and old.is_file():
        old.unlink()
    dest.write_bytes(data)
    _touch_marker(media_dir)
    return True


def remove_produto_image_at(slug: str, index: int) -> bool:
    """Drop storefront slot `index` and renumber the images that follow."""
    files = materialize_produto_gallery(slug)
    if index < 0 or index >= len(files):
        return False
    media_dir = files[0].parent if files else _ensure_media_dir(slug)
    if media_dir is None:
        return False
    kept = [
        (path.suffix, path.read_bytes())
        for position, path in enumerate(files)
        if position != index
    ]
    _clear_images(media_dir)
    for position, (suffix, data) in enumerate(kept):
        (media_dir / _numbered_name(position, suffix)).write_bytes(data)
    _touch_marker(media_dir)
    return True


def add_produto_image(slug: str, uploaded) -> str | None:
    """Append a PNG after the current storefront gallery. Returns the filename."""
    parsed = _read_upload(uploaded)
    if parsed is None:
        return None
    data, suffix = parsed
    files = materialize_produto_gallery(slug)
    media_dir = _ensure_media_dir(slug)
    if media_dir is None:
        return None
    name = _numbered_name(len(files), suffix)
    (media_dir / name).write_bytes(data)
    _touch_marker(media_dir)
    return name


def save_produto_images(slug: str, files) -> list[str]:
    """
    Save uploaded PNGs under media/produtos/<slug>/ in selection order
    as 01.png, 02.png, ... after any images already on the store.
    """
    saved: list[str] = []
    for uploaded in files:
        name = add_produto_image(slug, uploaded)
        if name:
            saved.append(name)
    return saved


def delete_produto_image(slug: str, filename: str) -> bool:
    """Delete a single media image. Returns True if deleted."""
    if not filename or not _SAFE_FILENAME.match(filename):
        return False
    if Path(filename).suffix.lower() not in ALLOWED_DISPLAY_SUFFIXES:
        return False
    media_dir = _safe_subdir(produto_media_base(), slug)
    if media_dir is None:
        return False
    target = (media_dir / filename).resolve()
    try:
        target.relative_to(media_dir)
    except ValueError:
        return False
    if target.is_file():
        target.unlink()
        return True
    return False


def delete_produto_media_dir(slug: str) -> None:
    """Remove media/produtos/<slug>/ and its contents if present."""
    media_dir = _safe_subdir(produto_media_base(), slug)
    if media_dir is None or not media_dir.is_dir():
        return
    for path in media_dir.iterdir():
        if path.is_file():
            path.unlink()
    try:
        media_dir.rmdir()
    except OSError:
        pass
