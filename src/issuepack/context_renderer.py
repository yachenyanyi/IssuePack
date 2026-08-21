from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path

from .models import Message, MessageType


_CLOCK_PATTERN = re.compile(r"^(?:上午|下午)?\s*\d{1,2}:\d{2}(?::\d{2})?$")


def _clean_space(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split())


def _split_display_time(value: str) -> tuple[str, str]:
    cleaned = _clean_space(value)
    if not cleaned:
        return "", ""
    parts = cleaned.rsplit(" ", 1)
    if len(parts) == 2 and _CLOCK_PATTERN.match(parts[1]):
        return parts[0], parts[1]
    return "", cleaned


def _speaker_aliases(messages: list[Message]) -> OrderedDict[str, str]:
    aliases: OrderedDict[str, str] = OrderedDict()
    for message in messages:
        sender = message.sender.strip() or "Unknown"
        if sender in aliases:
            continue
        index = len(aliases)
        alias = chr(ord("A") + index) if index < 26 else f"P{index + 1}"
        aliases[sender] = alias
    return aliases


def _compact_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip().replace("\n", " ↵ ")


def render_compact_context(
    title: str,
    messages: list[Message],
    asset_paths: dict[str, str] | None = None,
) -> str:
    """Render a token-conscious transcript for coding agents.

    The renderer intentionally optimizes only the agent-facing view. Exact event
    structure remains available in the package data layer.
    """
    asset_paths = asset_paths or {}
    aliases = _speaker_aliases(messages)
    lines = [f"# {title}"]

    if aliases:
        people = ";".join(f"{alias}={sender}" for sender, alias in aliases.items())
        lines.append(f"people:{people}")

    dated_times = [_split_display_time(message.time) for message in messages]
    unique_dates = []
    for date, _clock in dated_times:
        if date and date not in unique_dates:
            unique_dates.append(date)
    single_date = unique_dates[0] if len(unique_dates) == 1 else ""
    if single_date:
        lines.append(f"date:{single_date}")

    grouped: list[tuple[str, str, str, list[str]]] = []
    for message, (date, clock) in zip(messages, dated_times):
        sender = message.sender.strip() or "Unknown"
        alias = aliases.get(sender, sender)
        part = ""
        if message.type == MessageType.TEXT:
            part = _compact_text(message.content)
        elif message.type == MessageType.IMAGE:
            path = asset_paths.get(message.id)
            part = f"[img:{path}]" if path else "[img:missing]"
        elif message.type == MessageType.FILE:
            path = asset_paths.get(message.id)
            part = f"[file:{path}]" if path else "[file:missing]"
        if not part:
            continue

        effective_date = "" if single_date else date
        if grouped and grouped[-1][0] == effective_date and grouped[-1][1] == clock and grouped[-1][2] == alias:
            grouped[-1][3].append(part)
        else:
            grouped.append((effective_date, clock, alias, [part]))

    previous_date: str | None = None
    for date, clock, alias, parts in grouped:
        if date and date != previous_date:
            lines.append(f"@{date}")
            previous_date = date
        prefix = f"{clock} " if clock else ""
        lines.append(f"{prefix}{alias}> {' '.join(parts)}")

    return "\n".join(lines).rstrip() + "\n"


def agent_instructions() -> str:
    return """# IssuePack agent instructions

- Use `context.md` as the only default entrypoint for this issue package.
- Do not proactively open, enumerate, summarize, or ingest `data/` or `raw/`.
- Open only assets explicitly referenced by the relevant lines in `context.md`; do not bulk-read every asset.
- Read `data/messages.jsonl` only when exact message order, metadata, or an omitted detail is necessary to resolve the task.
- Read `raw/` only to resolve a contradiction, verify source fidelity, or recover information unavailable from `context.md` and `data/`; inspect the smallest specific source file needed.
- `result.md` is agent output, not source evidence. Do not use it as requirement input before completing the task.
"""
