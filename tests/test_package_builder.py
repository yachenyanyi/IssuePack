import json
from datetime import datetime
from pathlib import Path

from issuepack.models import Message, MessageType
from issuepack.package_builder import build_package


def test_builds_layered_package_and_binds_image(tmp_path: Path):
    image = tmp_path / "source.png"
    image.write_bytes(b"fake-image")
    messages = [
        Message("msg-001", "客户A", "8/17 10:21", MessageType.TEXT, "改这里"),
        Message("msg-002", "客户A", "8/17 10:22", MessageType.IMAGE, "图片"),
    ]

    package = build_package(
        tmp_path / "out",
        "移动端修改",
        messages,
        {"msg-002": image},
        now=datetime(2026, 8, 21, 10, 30, 0),
    )

    assert (package / "context.md").exists()
    assert (package / "AGENTS.md").exists()
    assert (package / "data" / "messages.jsonl").exists()
    assert not (package / "issue.md").exists()
    assert (package / "assets" / "i1.png").exists()

    rows = [
        json.loads(line)
        for line in (package / "data" / "messages.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert rows[1]["asset"] == "assets/i1.png"

    context = (package / "context.md").read_text(encoding="utf-8")
    assert "people:A=客户A" in context
    assert "date:8/17" in context
    assert "10:22 A> [img:assets/i1.png]" in context

    instructions = (package / "AGENTS.md").read_text(encoding="utf-8")
    assert "Use `context.md` as the only default entrypoint" in instructions
    assert "Do not proactively open" in instructions
    assert "`data/` or `raw/`" in instructions


def test_builds_package_from_recovered_source_asset_path(tmp_path: Path):
    image = tmp_path / "wecom-cache.jpg"
    image.write_bytes(b"fake-jpeg")
    messages = [
        Message(
            "msg-001",
            "客户A",
            "8/17 13:21:57",
            MessageType.IMAGE,
            "[image](file:///D:/fake.jpg)",
            source_asset_path=str(image),
        )
    ]

    package = build_package(
        tmp_path / "out",
        "自动恢复图片",
        messages,
        {},
        now=datetime(2026, 8, 21, 10, 30, 1),
    )

    assert (package / "assets" / "i1.jpg").read_bytes() == b"fake-jpeg"
    context = (package / "context.md").read_text(encoding="utf-8")
    assert "[img:assets/i1.jpg]" in context


def test_missing_asset_remains_explicit_in_context(tmp_path: Path):
    messages = [Message("msg-001", "客户A", "10:22", MessageType.IMAGE, "图片")]
    package = build_package(
        tmp_path / "out",
        "未补图片",
        messages,
        {},
        now=datetime(2026, 8, 21, 10, 31, 0),
    )
    assert "[img:missing]" in (package / "context.md").read_text(encoding="utf-8")


def test_raw_snapshots_are_separate_fallback_layer(tmp_path: Path):
    messages = [Message("msg-001", "客户A", "10:22", MessageType.TEXT, "改这里")]
    package = build_package(
        tmp_path / "out",
        "保留原始剪贴板",
        messages,
        {},
        now=datetime(2026, 8, 21, 10, 32, 0),
        raw_snapshots=[
            {
                "purpose": "initial",
                "plain_text": "原始聊天",
                "html_text": "<p>原始聊天</p>",
                "formats": ["text/plain", "text/html"],
            }
        ],
    )
    assert (package / "raw" / "clipboard-001.txt").read_text(encoding="utf-8") == "原始聊天"
    assert (package / "raw" / "clipboard-001.html").exists()
    manifest = json.loads((package / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest[0]["purpose"] == "initial"
