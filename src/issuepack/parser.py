from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

from .models import Message, MessageType


_IMAGE_MARKERS = {"图片", "[图片]", "【图片】", "image", "[image]", "[图片消息]"}
_FILE_MARKERS = {"文件", "[文件]", "【文件】", "file", "[file]", "[文件消息]"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_MARKDOWN_ASSET_PATTERN = re.compile(
    r"^!?\[(?P<label>[^\]]+)\]\((?P<uri>file:///.+)\)$",
    re.IGNORECASE,
)
_INLINE_ASSET_PATTERN = re.compile(
    r"!?\[[^\]]+\]\(file:///[^)]+\)",
    re.IGNORECASE,
)

# WeCom copy formats can differ slightly by client/version. Keep the parser permissive.
_HEADER_PATTERNS = [
    # 张三 2026-08-21 10:23[:45] / 张三 8/17 09:48:37
    re.compile(
        r"^(?P<sender>.+?)\s+(?P<time>(?:20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?|\d{1,2}[-/.]\d{1,2})\s+(?:上午|下午)?\s*\d{1,2}:\d{2}(?::\d{2})?)$"
    ),
    # 2026-08-21 10:23[:45] 张三
    re.compile(
        r"^(?P<time>(?:20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?|\d{1,2}[-/.]\d{1,2})\s+(?:上午|下午)?\s*\d{1,2}:\d{2}(?::\d{2})?)\s+(?P<sender>.+?)$"
    ),
    # 张三 10:23[:45] (same-day copy)
    re.compile(r"^(?P<sender>.+?)\s+(?P<time>(?:上午|下午)?\s*\d{1,2}:\d{2}(?::\d{2})?)$"),
]


@dataclass(slots=True)
class _Chunk:
    sender: str
    time: str
    header: str
    lines: list[str]


def _parse_header(line: str) -> tuple[str, str] | None:
    cleaned = line.strip()
    for pattern in _HEADER_PATTERNS:
        match = pattern.match(cleaned)
        if match:
            return match.group("sender").strip(), match.group("time").strip()
    return None


def _file_uri_to_local_path(uri: str) -> str | None:
    parsed = urlparse(uri)
    if parsed.scheme.lower() != "file":
        return None

    path = unquote(parsed.path)
    if parsed.netloc and parsed.netloc.lower() != "localhost":
        path = f"//{parsed.netloc}{path}"
    elif re.match(r"^/[A-Za-z]:/", path):
        path = path[1:]

    if os.name == "nt":
        path = path.replace("/", "\\")
    return path


def _asset_marker(line: str) -> tuple[MessageType, str | None] | None:
    normalized = line.strip()
    lowered = normalized.lower()
    if lowered in {marker.lower() for marker in _IMAGE_MARKERS}:
        return MessageType.IMAGE, None
    if lowered in {marker.lower() for marker in _FILE_MARKERS}:
        return MessageType.FILE, None

    match = _MARKDOWN_ASSET_PATTERN.match(normalized)
    if not match:
        return None

    label = match.group("label").strip().lower()
    uri = match.group("uri").strip()
    path = _file_uri_to_local_path(uri)
    suffix = os.path.splitext(urlparse(uri).path)[1].lower()

    if label in {"image", "图片", "图片消息"} or suffix in _IMAGE_SUFFIXES:
        return MessageType.IMAGE, path
    return MessageType.FILE, path


def parse_wecom_text(text: str) -> list[Message]:
    """Parse copied WeCom text without summarizing or rewriting content.

    Timestamps remain as displayed strings because same-day copies may omit the year/date.
    Rich clipboard media links such as ``[image](file:///D:/...)`` are preserved
    as source_asset_path so the package builder can copy the original file directly.
    Inline media links appended to ordinary text are split into separate timeline events while
    preserving their original order.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chunks: list[_Chunk] = []
    current: _Chunk | None = None

    for raw_line in lines:
        header = _parse_header(raw_line)
        if header:
            if current is not None:
                chunks.append(current)
            sender, time = header
            current = _Chunk(sender=sender, time=time, header=raw_line.strip(), lines=[])
            continue

        if current is None:
            if raw_line.strip():
                current = _Chunk(sender="Unknown", time="", header="", lines=[raw_line])
            continue
        current.lines.append(raw_line)

    if current is not None:
        chunks.append(current)

    messages: list[Message] = []

    def add_message(
        sender: str,
        time: str,
        msg_type: MessageType,
        content: str,
        header: str,
        source_asset_path: str | None = None,
    ) -> None:
        messages.append(
            Message(
                id=f"msg-{len(messages) + 1:03d}",
                sender=sender or "Unknown",
                time=time,
                type=msg_type,
                content=content,
                source_header=header,
                source_asset_path=source_asset_path,
            )
        )

    for chunk in chunks:
        text_buffer: list[str] = []

        def flush_text() -> None:
            content = "\n".join(text_buffer).strip("\n")
            text_buffer.clear()
            if content.strip():
                add_message(chunk.sender, chunk.time, MessageType.TEXT, content, chunk.header)

        for line in chunk.lines:
            inline_assets = list(_INLINE_ASSET_PATTERN.finditer(line))
            if inline_assets:
                cursor = 0
                for match in inline_assets:
                    before = line[cursor : match.start()]
                    if before:
                        text_buffer.append(before)
                    flush_text()
                    marker_text = match.group(0)
                    marker = _asset_marker(marker_text)
                    if marker is not None:
                        message_type, source_asset_path = marker
                        add_message(
                            chunk.sender,
                            chunk.time,
                            message_type,
                            marker_text,
                            chunk.header,
                            source_asset_path=source_asset_path,
                        )
                    cursor = match.end()
                after = line[cursor:]
                if after:
                    text_buffer.append(after)
                continue

            marker = _asset_marker(line)
            if marker is not None:
                flush_text()
                message_type, source_asset_path = marker
                add_message(
                    chunk.sender,
                    chunk.time,
                    message_type,
                    line.strip(),
                    chunk.header,
                    source_asset_path=source_asset_path,
                )
            else:
                text_buffer.append(line)
        flush_text()

    return messages
