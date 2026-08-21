from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"


@dataclass(slots=True)
class Message:
    id: str
    sender: str
    time: str
    type: MessageType
    content: str = ""
    source_header: str = ""
    asset_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["type"] = self.type.value
        return data
