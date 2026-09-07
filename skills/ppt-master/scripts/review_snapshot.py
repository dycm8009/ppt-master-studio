#!/usr/bin/env python3
"""PPT Master - Immutable actual-SVG review snapshot.

Resolve prepared assets using the shared resource resolver, embed them without
rasterizing pages, and bind the exact bytes used by the preview. No source files
are modified and no network resources are fetched.

Usage:
    Imported by deck_review_handoff.
Examples:
    snapshot_svg(Path('projects/demo/svg_output/P01.svg'))
Dependencies:
    Standard library and existing PPT Master resource/icon helpers.
"""
from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path
from urllib.parse import unquote_to_bytes, urlsplit
from xml.etree import ElementTree as ET

from resource_paths import project_root_for_svg_path, resolve_external_image_reference

SVG_NS = 'http://www.w3.org/2000/svg'
XLINK_NS = 'http://www.w3.org/1999/xlink'
MIME = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml',
        '.avif': 'image/avif', '.bmp': 'image/bmp'}
ACTIVE = {'script', 'foreignobject', 'animate', 'animatetransform', 'animatemotion', 'set', 'discard'}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1].lower()


def snapshot_svg(path: Path) -> tuple[str, str, list[dict[str, str]]]:
    """Return raw-SVG hash, inert browser SVG, and prepared-resource digests."""
    project = project_root_for_svg_path(path).resolve()
    path = path.resolve()
    cache: dict[Path, bytes] = {}

    def read(source: Path) -> bytes:
        source = source.resolve()
        if not source.is_relative_to(project):
            raise RuntimeError(f'review resource escapes project: {source.name}')
        if source not in cache:
            cache[source] = source.read_bytes()
        return cache[source]

    def markup(raw: bytes, source: Path, depth: int = 0) -> ET.Element:
        if depth > 12:
            raise RuntimeError('review SVG resource cycle or excessive nesting; prepare closed assets')
        if re.search(br'<!\s*(?:DOCTYPE|ENTITY)\b', raw, re.I):
            raise RuntimeError(f'unsafe XML declaration in {source.name}; prepare a plain SVG')
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise RuntimeError(f"invalid SVG: {source.name}; repair its XML") from exc
        if root.tag not in {'svg', '{' + SVG_NS + '}svg'}:
            raise RuntimeError(f'not an SVG root: {source.name}')

        def scrub(node: ET.Element) -> None:
            for child in list(node):
                kind = local_name(child.tag)
                if kind in ACTIVE or (child.tag.startswith('{') and not child.tag.startswith('{' + SVG_NS + '}')):
                    node.remove(child)
                    continue
                if kind == 'style':
                    raise RuntimeError(f'embedded stylesheet in {source.name}; inline styles in the owning source')
                if kind == 'use' and child.get('data-icon'):
                    from svg_finalize.embed_icons import (
                        extract_paths_from_icon, generate_icon_group, parse_use_element, resolve_icon_path,
                    )
                    icon, _ = resolve_icon_path(child.attrib['data-icon'], project / 'icons')
                    read(icon)  # Project-local only; no global-library fallback.
                    attrs = parse_use_element(ET.tostring(child, encoding='unicode'))
                    elements, style, size = extract_paths_from_icon(icon, target_dir=source.parent)
                    if not elements:
                        raise RuntimeError(f'empty review icon: {icon.name}; repair the prepared asset')
                    group = ET.fromstring(generate_icon_group(attrs, elements, style, size))
                    group.tail = child.tail
                    node.insert(list(node).index(child), group)
                    node.remove(child)
                    child = group
                scrub(child)
            for key, value in list(node.attrib.items()):
                name = local_name(key)
                if key == '{http://www.w3.org/XML/1998/namespace}base':
                    raise RuntimeError('xml:base is not supported in a closed review snapshot')
                if name.startswith('on') or 'javascript:' in re.sub(r'\s+', '', value).lower():
                    del node.attrib[key]
                    continue
                if name == 'href':
                    if local_name(node.tag) == 'a':
                        del node.attrib[key]  # Review must not navigate away.
                    elif local_name(node.tag) == 'image':
                        node.attrib[key] = image(value, source, depth + 1)
                    elif not value.startswith('#'):
                        raise RuntimeError(f'unsupported external SVG reference in {source.name}; inline it first')
                if 'url(' in value.lower():
                    refs = re.findall(r'url\(\s*([^)]+?)\s*\)', value, re.I)
                    if any(not ref.strip(' \"\'').startswith('#') for ref in refs):
                        raise RuntimeError(f'external CSS resource in {source.name}; prepare a local image')
        scrub(root)
        # Slide-local IDs must never shadow controls in the surrounding HTML.
        prefix = 'review-' + digest(raw)[:12] + '-'
        ids = {node.get('id') for node in root.iter() if node.get('id')}
        for node in root.iter():
            if node.get('id'):
                node.set('id', prefix + node.get('id'))
            for key, value in list(node.attrib.items()):
                if local_name(key) == 'href' and value.startswith('#') and value[1:] in ids:
                    node.set(key, '#' + prefix + value[1:])
                elif 'url(' in value.lower():
                    value = re.sub(r"url\(\s*['\"]?#([^)'\"\s]+)['\"]?\s*\)",
                                   lambda m: 'url(#' + prefix + m[1] + ')' if m[1] in ids else m[0], value)
                    node.set(key, value)
                elif key in {'aria-labelledby', 'aria-describedby'}:
                    node.set(key, ' '.join(prefix + item if item in ids else item for item in value.split()))
        return root

    def image(href: str, source: Path, depth: int) -> str:
        if href.startswith('data:'):
            header, sep, payload = href.partition(',')
            mime = header[5:].split(';')[0].lower()
            if not sep or mime not in MIME.values():
                raise RuntimeError('unsupported review image data URI')
            data = base64.b64decode(payload, validate=True) if ';base64' in header else unquote_to_bytes(payload)
        else:
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc:
                raise RuntimeError('review images must be prepared project-local assets, not network URLs')
            asset = resolve_external_image_reference(source.parent, href)
            if asset is None:
                raise RuntimeError(f'review image missing: {href}; prepare it before review')
            data = read(asset)
            source = asset
            mime = MIME.get(asset.suffix.lower())
            if mime is None:
                raise RuntimeError(f'browser cannot review {asset.suffix}; no silent image substitution is allowed')
        if mime == 'image/svg+xml':
            data = serialize(markup(data, source, depth)).encode('utf-8')
        return f'data:{mime};base64,' + base64.b64encode(data).decode('ascii')

    def serialize(root: ET.Element) -> str:
        # HTML parsers do not turn <ns0:svg> into SVG elements.
        ET.register_namespace('', SVG_NS)
        ET.register_namespace('xlink', XLINK_NS)
        return ET.tostring(root, encoding='unicode', xml_declaration=False)

    raw = read(path)
    root = markup(raw, path)
    root.set('data-ppt-master-review-slide', path.name)
    root.set('style', root.get('style', '') + ';max-width:100%;max-height:100%;display:block;margin:auto')
    preview = serialize(root)
    for source, before in cache.items():
        if source.read_bytes() != before:
            raise RuntimeError('review source changed during snapshot; rebuild review')
    resources = [{'path': source.relative_to(project).as_posix(), 'sha256': digest(data)}
                 for source, data in sorted(cache.items()) if source != path]
    return digest(raw), preview, resources
