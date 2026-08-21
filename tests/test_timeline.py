from pathlib import Path

from issuepack.models import Message, MessageType
from issuepack.timeline import reindex_messages


def test_reindex_keeps_assets_bound_after_reorder(tmp_path: Path):
    image_a = tmp_path / "a.png"
    image_b = tmp_path / "b.png"
    messages = [
        Message("msg-001", "A", "10:00", MessageType.TEXT, "one"),
        Message("msg-002", "A", "10:01", MessageType.IMAGE, "image-a"),
        Message("msg-003", "B", "10:02", MessageType.IMAGE, "image-b"),
    ]
    assets = {"msg-002": image_a, "msg-003": image_b}

    moved = messages.pop(2)
    messages.insert(1, moved)
    remapped = reindex_messages(messages, assets)

    assert [message.id for message in messages] == ["msg-001", "msg-002", "msg-003"]
    assert messages[1].content == "image-b"
    assert remapped["msg-002"] == image_b
    assert remapped["msg-003"] == image_a


def test_reindex_drops_asset_for_deleted_message(tmp_path: Path):
    image = tmp_path / "deleted.png"
    messages = [
        Message("msg-001", "A", "10:00", MessageType.TEXT, "one"),
        Message("msg-003", "B", "10:02", MessageType.TEXT, "three"),
    ]
    assets = {"msg-002": image}

    remapped = reindex_messages(messages, assets)

    assert [message.id for message in messages] == ["msg-001", "msg-002"]
    assert remapped == {}
