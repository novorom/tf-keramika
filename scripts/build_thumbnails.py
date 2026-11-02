#!/usr/bin/env python3
"""Build small WebP thumbnails for catalogue and collection listing cards."""

from __future__ import annotations

import re
import os
from pathlib import Path
from urllib.parse import unquote

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
MAX_SIZE = (320, 320)
IMG_TAG = re.compile(r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])([^"\']+)(\2)', re.I | re.S)


def make_thumbnail(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image = ImageOps.fit(image, MAX_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        image.save(destination, "WEBP", quality=80, method=6)


def rewrite_listing(path: Path, cache: dict[Path, Path]) -> bool:
    original = path.read_text(encoding="utf-8")
    changed = False

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        src = match.group(3)
        marker = "img/photos/"
        if marker not in src or "img/thumbs/" in src:
            return match.group(0)

        prefix, filename = src.rsplit(marker, 1)
        source = (path.parent / unquote(prefix + marker + filename)).resolve()
        if not source.is_file() or ROOT not in source.parents:
            return match.group(0)

        thumb_name = source.stem + ".webp"
        thumb = ROOT / "img" / "thumbs" / thumb_name
        if source not in cache:
            make_thumbnail(source, thumb)
            cache[source] = thumb

        relative = Path(os.path.relpath(thumb, path.parent)).as_posix()
        changed = True
        return match.group(1) + match.group(2) + relative + match.group(4)

    rewritten = IMG_TAG.sub(replace, original)
    if changed:
        path.write_text(rewritten, encoding="utf-8")
    return changed


def main() -> None:
    cache: dict[Path, Path] = {}
    rebuilt = 0
    photo_dir = ROOT / "img" / "photos"
    for thumb in (ROOT / "img" / "thumbs").glob("*.webp"):
        sources = sorted(photo_dir.glob(f"{thumb.stem}.*"))
        if sources:
            make_thumbnail(sources[0], thumb)
            rebuilt += 1

    pages = [
        page
        for page in ROOT.rglob("*.html")
        if ".git" not in page.parts and "products" not in page.relative_to(ROOT).parts
    ]
    updated = [page for page in pages if rewrite_listing(page, cache)]
    print(f"Built or refreshed {rebuilt + len(cache)} thumbnails; updated {len(updated)} listing pages.")


if __name__ == "__main__":
    main()
