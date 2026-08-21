from __future__ import annotations

from pathlib import Path

from .models import Message


def reindex_messages(messages: list[Message], captured_assets: dict[str, Path]) -> dict[str, Path]:
    """Renumber timeline messages while keeping captured assets bound to the same message objects.

    Message IDs are presentation/package identifiers, not stable identities. Timeline edits can
    insert, move, or delete rows, so IDs must be regenerated from the final order. Any staged
    attachment keyed by the previous ID is remapped to the new ID before the message IDs change.
    """
    old_to_new: dict[str, str] = {}
    for index, message in enumerate(messages, start=1):
        old_to_new[message.id] = f"msg-{index:03d}"

    remapped_assets = {
        old_to_new[old_id]: path
        for old_id, path in captured_assets.items()
        if old_id in old_to_new
    }

    for index, message in enumerate(messages, start=1):
        message.id = f"msg-{index:03d}"

    return remapped_assets
