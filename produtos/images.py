"""Helpers to resolve and manage product image paths safely (no path traversal)."""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import Produto, ProdutoImagem

ALLOWED_UPLOAD_SUFFIXES = {'.png'}
# Legacy static assets (e.g. SVG) still listed on the storefront.
ALLOWED_DISPLAY_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'}
ALLOWED_IMAGE_SUFFIXES = ALLOWED_DISPLAY_SUFFIXES  # alias for listing/delete
_SAFE_SLUG = re.compile(r'^[a-z0-9\-]+$')
_SAFE_FILENAME = re.compile(r'^[a-zA-Z0-9._\-]+$')
_NUMBERED_NAME = re.compile(r'^(\d{2})(\.[a-z0-9]+)$')
# Marks media/produtos/<slug>/ as the storefront source even when empty,
# so removing the last image does not fall back to static files.
_GALLERY_MARKER = '.galeria'
_CONTENT_TYPES = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
}


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


def _media_is_source(media_dir: Path | None) -> bool:
    if media_dir is None or not media_dir.is_dir():
        return False
    return bool(_list_files(media_dir)) or _marker_path(media_dir).is_file()


def _produto_for(slug: str) -> Produto | None:
    if not _slug_ok(slug):
        return None
    return Produto.objects.filter(slug=slug).first()


def _gallery_paths(slug: str) -> tuple[list[Path], str]:
    """Files currently shown on disk, plus 'media' or 'static'."""
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


def _db_public_url(slug: str, row: ProdutoImagem) -> str:
    name = _numbered_name(row.ordem, row.sufixo)
    version = int(row.atualizado.timestamp())
    base = settings.MEDIA_URL.rstrip('/')
    return f'{base}/produtos/{slug}/{name}?v={version}'


def _gallery_from_db(produto: Produto) -> list[dict]:
    return [
        {
            'index': row.ordem,
            'name': _numbered_name(row.ordem, row.sufixo),
            'url': _db_public_url(produto.slug, row),
            'source': 'database',
        }
        for row in produto.imagens.all()
    ]


def list_produto_gallery(slug: str, produto: Produto | None = None) -> list[dict]:
    """Storefront order as {index, name, url, source}."""
    if produto is None:
        produto = _produto_for(slug)
    elif produto.slug:
        slug = produto.slug
    if produto is not None and produto.galeria_no_banco:
        return _gallery_from_db(produto)

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


def list_produto_images(slug: str, produto: Produto | None = None) -> list[str]:
    """
    Return absolute URL paths for product images.
    Prefers rows in ProdutoImagem; then media/produtos/<slug>/;
    then static/images/produtos/<slug>/.
    """
    return [item['url'] for item in list_produto_gallery(slug, produto)]


def first_produto_image(slug: str) -> str | None:
    images = list_produto_images(slug)
    return images[0] if images else None


def list_produto_media_images(slug: str) -> list[dict]:
    """Return stored images as {name, url}, in storefront order."""
    return [
        {'name': item['name'], 'url': item['url']}
        for item in list_produto_gallery(slug)
        if item['source'] in ('media', 'database')
    ]


def _max_bytes() -> int:
    return getattr(settings, 'MAX_PRODUTO_IMAGE_BYTES', 1 * 1024 * 1024)


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


def materialize_produto_gallery(slug: str) -> bool:
    """
    Copy the gallery the store shows into ProdutoImagem as 01.ext, 02.ext, ...
    Static originals and any legacy media files are not deleted.
    """
    produto = _produto_for(slug)
    if produto is None:
        return False
    if produto.galeria_no_banco:
        return True

    files, _source = _gallery_paths(slug)
    with transaction.atomic():
        produto.imagens.all().delete()
        for index, path in enumerate(files):
            ProdutoImagem.objects.create(
                produto=produto,
                ordem=index,
                sufixo=path.suffix.lower(),
                conteudo=path.read_bytes(),
            )
        produto.galeria_no_banco = True
        produto.save(update_fields=['galeria_no_banco'])
    return True


def replace_produto_image(slug: str, index: int, uploaded) -> bool:
    """Overwrite storefront slot `index` (0 = first image) with a PNG upload."""
    parsed = _read_upload(uploaded)
    if parsed is None or index < 0:
        return False
    data, suffix = parsed
    if not materialize_produto_gallery(slug):
        return False
    produto = _produto_for(slug)
    if produto is None:
        return False
    row = produto.imagens.filter(ordem=index).first()
    if row is None:
        return False
    row.conteudo = data
    row.sufixo = suffix
    row.save()
    return True


def remove_produto_image_at(slug: str, index: int) -> bool:
    """Drop storefront slot `index` and renumber the images that follow."""
    if index < 0 or not materialize_produto_gallery(slug):
        return False
    produto = _produto_for(slug)
    if produto is None:
        return False
    rows = list(produto.imagens.order_by('ordem'))
    if index >= len(rows):
        return False
    kept = [
        (row.sufixo, bytes(row.conteudo))
        for position, row in enumerate(rows)
        if position != index
    ]
    with transaction.atomic():
        produto.imagens.all().delete()
        for position, (suffix, data) in enumerate(kept):
            ProdutoImagem.objects.create(
                produto=produto,
                ordem=position,
                sufixo=suffix,
                conteudo=data,
            )
    return True


def add_produto_image(slug: str, uploaded) -> str | None:
    """Append a PNG after the current storefront gallery. Returns the filename."""
    parsed = _read_upload(uploaded)
    if parsed is None:
        return None
    data, suffix = parsed
    if not materialize_produto_gallery(slug):
        return None
    produto = _produto_for(slug)
    if produto is None:
        return None
    ordem = produto.imagens.count()
    ProdutoImagem.objects.create(
        produto=produto,
        ordem=ordem,
        sufixo=suffix,
        conteudo=data,
    )
    return _numbered_name(ordem, suffix)


def save_produto_images(slug: str, files) -> list[str]:
    """
    Save uploaded PNGs in ProdutoImagem, in selection order,
    as 01.png, 02.png, ... after any images already on the store.
    """
    saved: list[str] = []
    for uploaded in files:
        name = add_produto_image(slug, uploaded)
        if name:
            saved.append(name)
    return saved


def delete_produto_image(slug: str, filename: str) -> bool:
    """Delete one stored image. Returns True if deleted."""
    if not filename or not _SAFE_FILENAME.match(filename):
        return False
    if Path(filename).suffix.lower() not in ALLOWED_DISPLAY_SUFFIXES:
        return False
    produto = _produto_for(slug)
    if produto is not None and produto.galeria_no_banco:
        for row in produto.imagens.all():
            if _numbered_name(row.ordem, row.sufixo) == filename:
                return remove_produto_image_at(slug, row.ordem)
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
    """Remove stored images for the slug, including a legacy media folder."""
    produto = _produto_for(slug)
    if produto is not None:
        produto.imagens.all().delete()
        if produto.galeria_no_banco:
            produto.galeria_no_banco = False
            produto.save(update_fields=['galeria_no_banco'])
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


def read_produto_image(slug: str, filename: str) -> tuple[bytes, str] | None:
    """Return (bytes, content type) for a public /media/produtos/<slug>/<file> URL."""
    if not _slug_ok(slug) or not filename or not _SAFE_FILENAME.match(filename):
        return None
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_DISPLAY_SUFFIXES:
        return None

    produto = _produto_for(slug)
    if produto is not None and produto.galeria_no_banco:
        match = _NUMBERED_NAME.match(filename)
        if not match:
            return None
        ordem = int(match.group(1)) - 1
        if ordem < 0:
            return None
        row = produto.imagens.filter(ordem=ordem).first()
        if row is None or row.sufixo.lower() != suffix:
            return None
        content_type = _CONTENT_TYPES.get(row.sufixo.lower())
        if content_type is None:
            return None
        return bytes(row.conteudo), content_type

    media_dir = _safe_subdir(produto_media_base(), slug)
    if media_dir is None:
        return None
    target = (media_dir / filename).resolve()
    try:
        target.relative_to(media_dir)
    except ValueError:
        return None
    if not target.is_file():
        return None
    content_type = _CONTENT_TYPES.get(suffix)
    if content_type is None:
        return None
    return target.read_bytes(), content_type
