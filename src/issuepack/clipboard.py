from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QGuiApplication, QImage

from .models import MessageType


class ClipboardCaptureError(RuntimeError):
    pass


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def capture_clipboard_asset(destination_dir: Path, message_id: str, expected: MessageType) -> Path:
    """Capture the current clipboard file/image into a stable temporary path.

    Qt exposes Windows file-drop clipboard entries as file URLs on supported clients,
    allowing IssuePack to copy a WeCom temporary media file before it disappears.
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
