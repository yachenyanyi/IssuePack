from __future__ import annotations

import html as html_lib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QGuiApplication, QImage

from .models import MessageType


class ClipboardCaptureError(RuntimeError):
    pass


@dataclass(slots=True)
class ClipboardConversation:
    enriched_text: str
    plain_text: str
    html_text: str
    formats: list[str]


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_IMAGE_MARKER_LINE = re.compile(r"(?im)^(?P<indent>\s*)(?:\[?图片\]?|\[?image\]?|【图片】|\[图片消息\])(?P<trail>\s*)$")
_LOCAL_FILE_ATTR = re.compile(
    r'''(?is)\b(?:src|href)\s*=\s*["'](?P<uri>file:///[^"']+)["']'''
)


def _is_image_uri(uri: str) -> bool:
    lower = uri.lower().split("?", 1)[0].split("#", 1)[0]
    return any(lower.endswith(suffix) for suffix in _IMAGE_SUFFIXES)


def enrich_plain_text_with_html_assets(plain_text: str, html_text: str) -> str:
    """Restore local image links that WeCom exposes only in rich clipboard HTML.

    WeCom's plain-text clipboard flavor may contain only ``[图片]`` while the
    rich HTML flavor still contains ``file:///...`` URLs. Keep the reliable
    plain-text message ordering/header format, but replace image placeholders
    with the corresponding local file URL in order.
    """
    if not plain_text or not html_text:
        return plain_text

    if "file:///" in plain_text.lower():
        return plain_text

    image_uris: list[str] = []
    seen: set[str] = set()
    for match in _LOCAL_FILE_ATTR.finditer(html_text):
        uri = html_lib.unescape(match.group("uri"))
        if _is_image_uri(uri) and uri not in seen:
            seen.add(uri)
            image_uris.append(uri)

    if not image_uris:
        return plain_text

    iterator = iter(image_uris)

    def replace_marker(match: re.Match[str]) -> str:
        try:
            uri = next(iterator)
        except StopIteration:
            return match.group(0)
        return f"{match.group('indent')}[image]({uri}){match.group('trail')}"

    return _IMAGE_MARKER_LINE.sub(replace_marker, plain_text)


def read_clipboard_conversation_payload() -> ClipboardConversation:
    """Read both the original and agent-friendly WeCom clipboard flavors."""
    clipboard = QGuiApplication.clipboard()
    mime: QMimeData = clipboard.mimeData()
    formats = list(mime.formats())
    plain = mime.text() if mime.hasText() else ""
    html_text = mime.html() if mime.hasHtml() else ""
    enriched = enrich_plain_text_with_html_assets(plain, html_text) if html_text else plain
    return ClipboardConversation(
        enriched_text=enriched,
        plain_text=plain,
        html_text=html_text,
        formats=formats,
    )


def read_clipboard_conversation_text() -> tuple[str, list[str]]:
    """Compatibility wrapper returning enriched text and available MIME formats."""
    payload = read_clipboard_conversation_payload()
    return payload.enriched_text, payload.formats


def capture_clipboard_asset(destination_dir: Path, message_id: str, expected: MessageType) -> Path:
    """Capture the current clipboard file/image into a stable temporary path.

    This remains a fallback for media that could not be recovered automatically
    from the original multi-message rich clipboard payload.
    """
    clipboard = QGuiApplication.clipboard()
    mime: QMimeData = clipboard.mimeData()
    destination_dir.mkdir(parents=True, exist_ok=True)

    if mime.hasUrls():
        local_files = [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile()]
        local_files = [path for path in local_files if path.exists() and path.is_file()]
        if local_files:
            source = local_files[0]
            if expected == MessageType.IMAGE and source.suffix.lower() not in _IMAGE_SUFFIXES:
                raise ClipboardCaptureError(f"剪贴板文件不是图片: {source.name}")
            target = destination_dir / f"{message_id}{source.suffix.lower() or '.bin'}"
            shutil.copy2(source, target)
            return target

    if expected == MessageType.IMAGE and mime.hasImage():
        image = clipboard.image()
        if image.isNull():
            raise ClipboardCaptureError("剪贴板包含图片格式，但无法读取图片数据。")
        target = destination_dir / f"{message_id}.png"
        if not QImage(image).save(str(target), "PNG"):
            raise ClipboardCaptureError("无法保存剪贴板图片。")
        return target

    if expected == MessageType.IMAGE:
        raise ClipboardCaptureError("当前剪贴板没有可读取的图片。请在企业微信里复制对应图片后重试。")
    raise ClipboardCaptureError("当前剪贴板没有可读取的文件。请在企业微信里复制对应文件后重试。")
