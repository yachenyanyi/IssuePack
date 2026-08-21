from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .context_renderer import agent_instructions, render_compact_context
from .models import Message, MessageType


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "-", value.strip())
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-.")
    return cleaned[:60] or "issue"


def source_asset_for(message: Message) -> Path | None:
    if not message.source_asset_path:
        return None
    source = Path(message.source_asset_path)
    if source.exists() and source.is_file():
        return source
    return None


def _copy_asset(source: Path, package_dir: Path, short_name: str) -> str:
    assets_dir = package_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower() or ".bin"
    target = assets_dir / f"{short_name}{suffix}"
    shutil.copy2(source, target)
    return target.relative_to(package_dir).as_posix()


def _message_row(message: Message) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": message.id,
        "time": message.time,
        "sender": message.sender,
        "type": message.type.value,
    }
    if message.content:
        row["content"] = message.content
    if message.asset_path:
        row["asset"] = message.asset_path
    return row


def _write_raw_snapshots(package_dir: Path, snapshots: list[dict[str, Any]]) -> None:
    if not snapshots:
        return

    raw_dir = package_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []

    for index, snapshot in enumerate(snapshots, start=1):
        stem = f"clipboard-{index:03d}"
        plain = str(snapshot.get("plain_text") or "")
        html = str(snapshot.get("html_text") or "")
        entry: dict[str, Any] = {
            "id": stem,
            "purpose": snapshot.get("purpose") or "source",
            "formats": snapshot.get("formats") or [],
        }
        if plain:
            plain_name = f"{stem}.txt"
            (raw_dir / plain_name).write_text(plain, encoding="utf-8")
            entry["text"] = plain_name
        if html:
            html_name = f"{stem}.html"
            (raw_dir / html_name).write_text(html, encoding="utf-8")
            entry["html"] = html_name
        manifest.append(entry)

    (raw_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_package(
    output_root: Path,
    title: str,
    messages: list[Message],
    captured_assets: dict[str, Path],
    now: datetime | None = None,
    raw_snapshots: list[dict[str, Any]] | None = None,
) -> Path:
    now = now or datetime.now()
    folder = f"{now:%Y-%m-%d-%H%M%S}-{_slugify(title)}"
    package_dir = output_root.expanduser().resolve() / folder
    if package_dir.exists():
        raise FileExistsError(f"Issue Package 已存在: {package_dir}")

    package_dir.mkdir(parents=True, exist_ok=False)
    (package_dir / "data").mkdir()

    finalized: list[Message] = []
    asset_paths: dict[str, str] = {}
    image_index = 0
    file_index = 0

    for source_message in messages:
        message = Message(
            id=source_message.id,
            sender=source_message.sender,
            time=source_message.time,
            type=source_message.type,
            content=source_message.content,
            source_header=source_message.source_header,
            asset_path=None,
            source_asset_path=source_message.source_asset_path,
        )
        asset = captured_assets.get(message.id) or source_asset_for(message)
        if asset is not None:
            if message.type == MessageType.IMAGE:
                image_index += 1
                short_name = f"i{image_index}"
            else:
                file_index += 1
                short_name = f"f{file_index}"
            message.asset_path = _copy_asset(asset, package_dir, short_name)
            asset_paths[message.id] = message.asset_path
        finalized.append(message)

    meta = {
        "schema_version": "0.3",
        "created_at": now.isoformat(timespec="seconds"),
        "title": title,
        "event_count": len(finalized),
        "agent_entrypoint": "context.md",
    }
    (package_dir / "data" / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    jsonl = "".join(
        json.dumps(_message_row(message), ensure_ascii=False, separators=(",", ":")) + "\n"
        for message in finalized
    )
    (package_dir / "data" / "messages.jsonl").write_text(jsonl, encoding="utf-8")

    (package_dir / "context.md").write_text(
        render_compact_context(title, finalized, asset_paths),
        encoding="utf-8",
    )
    (package_dir / "AGENTS.md").write_text(agent_instructions(), encoding="utf-8")
    _write_raw_snapshots(package_dir, raw_snapshots or [])

    (package_dir / "result.md").write_text(
        "# Resolution\n\n"
        "## Requirement understood\n\n"
        "## Files changed\n\n"
        "## Verification\n\n"
        "## Remaining uncertainties\n",
        encoding="utf-8",
    )
    return package_dir
