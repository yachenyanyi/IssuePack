import json
from datetime import datetime
from pathlib import Path

from issuepack.models import Message, MessageType
from issuepack.package_builder import build_package


def test_builds_package_and_binds_image(tmp_path: Path):
    image = tmp_path / "source.png"
    image.write_bytes(b"fake-image")
    messages = [
        Message("msg-001", "客户A", "10:21", MessageType.TEXT, "改这里"),
        Message("msg-002", "客户A", "10:22", MessageType.IMAGE, "图片"),
    ]

    package = build_package(
        tmp_path / "out",
        "移动端修改",
        messages,
        {"msg-002": image},
        now=datetime(2026, 8, 21, 10, 30, 0),
    )

    assert (package / "issue.md").exists()
    assert (package / "images" / "msg-002-image.png").exists()
    payload = json.loads((package / "raw" / "conversation.json").read_text(encoding="utf-8"))
    assert payload["messages"][1]["asset_path"] == "images/msg-002-image.png"
    markdown = (package / "issue.md").read_text(encoding="utf-8")
    assert "![msg-002 customer image](./images/msg-002-image.png)" in markdown


def test_missing_asset_remains_explicit(tmp_path: Path):
    messages = [Message("msg-001", "客户A", "10:22", MessageType.IMAGE, "图片")]
    package = build_package(
        tmp_path / "out",
        "未补图片",
        messages,
        {},
        now=datetime(2026, 8, 21, 10, 31, 0),
    )
    assert "[未补充图片：msg-001]" in (package / "issue.md").read_text(encoding="utf-8")
