from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Message, MessageType


_IMAGE_MARKERS = {"图片", "[图片]", "【图片】", "image", "[image]", "[图片消息]"}
_FILE_MARKERS = {"文件", "[文件]", "【文件】", "file", "[file]", "[文件消息]"}

# WeCom copy formats can differ slightly by client/version. Keep the parser permissive.
_HEADER_PATTERNS = [
    # 张三 2026-08-21 10:23[:45]
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


def _marker_type(line: str) -> MessageType | None:
    normalized = line.strip().lower()
    if normalized in {marker.lower() for marker in _IMAGE_MARKERS}:
        return MessageType.IMAGE
    if normalized in {marker.lower() for marker in _FILE_MARKERS}:
        return MessageType.FILE
    return None


def parse_wecom_text(text: str) -> list[Message]:
    """Parse copied WeCom text without summarizing or rewriting content.

    Timestamps remain as displayed strings because same-day copies may omit the year/date.
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

    def add_message(sender: str, time: str, msg_type: MessageType, content: str, header: str) -> None:
        messages.append(
            Message(
                id=f"msg-{len(messages) + 1:03d}",
                sender=sender or "Unknown",
                time=time,
                type=msg_type,
                content=content,
                source_header=header,
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
            marker = _marker_type(line)
            if marker is not None:
                flush_text()
                add_message(chunk.sender, chunk.time, marker, line.strip(), chunk.header)
            else:
                text_buffer.append(line)
        flush_text()

    return messages
