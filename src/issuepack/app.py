from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from .clipboard import ClipboardCaptureError, capture_clipboard_asset, read_clipboard_conversation_text
from .models import Message, MessageType
from .package_builder import build_package, source_asset_for
from .parser import parse_wecom_text


class IssuePackWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IssuePack V0")
        self.resize(980, 720)

        self.messages: list[Message] = []
        self.captured_assets: dict[str, Path] = {}
        self.session_dir = Path(tempfile.mkdtemp(prefix="issuepack-session-"))
        self.last_package: Path | None = None

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("例如：移动端首页产品区调整")

        default_root = Path.home() / "Documents" / "IssuePack" / "issues"
        self.output_edit = QLineEdit(str(default_root))
        browse_button = QPushButton("选择目录")
        browse_button.clicked.connect(self.choose_output_dir)

        self.chat_edit = QPlainTextEdit()
        self.chat_edit.setPlaceholderText(
            "复制企业微信聊天记录后，点击“读取剪贴板”。\n\n"
            "IssuePack 会优先读取富剪贴板中的本地图片路径，不会总结聊天内容。"
        )

        paste_button = QPushButton("读取剪贴板")
        paste_button.clicked.connect(self.load_clipboard_text)
        parse_button = QPushButton("解析聊天")
        parse_button.clicked.connect(self.parse_chat)

        self.placeholder_list = QListWidget()
        self.placeholder_list.setMinimumWidth(330)

        self.capture_button = QPushButton("捕获下一个未解析附件")
        self.capture_button.clicked.connect(self.capture_next_asset)
        self.capture_button.setEnabled(False)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)

        generate_button = QPushButton("生成 Issue Package")
        generate_button.clicked.connect(self.generate_package)
        open_button = QPushButton("打开最近生成目录")
        open_button.clicked.connect(self.open_last_package)

        self.status_label = QLabel("等待聊天记录")
        self.status_label.setWordWrap(True)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        meta = QGroupBox("Issue")
        meta_layout = QGridLayout(meta)
        meta_layout.addWidget(QLabel("标题"), 0, 0)
        meta_layout.addWidget(self.title_edit, 0, 1, 1, 2)
        meta_layout.addWidget(QLabel("输出目录"), 1, 0)
        meta_layout.addWidget(self.output_edit, 1, 1)
        meta_layout.addWidget(browse_button, 1, 2)
        layout.addWidget(meta)

        body = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("企业微信聊天原文"))
        left.addWidget(self.chat_edit, 1)
        left_actions = QHBoxLayout()
        left_actions.addWidget(paste_button)
        left_actions.addWidget(parse_button)
        left.addLayout(left_actions)
        body.addLayout(left, 2)

        right = QVBoxLayout()
        right.addWidget(QLabel("附件（优先自动恢复，失败时手动捕获）"))
        right.addWidget(self.placeholder_list, 1)
        right.addWidget(self.capture_button)
        right.addWidget(self.progress)
        body.addLayout(right, 1)
        layout.addLayout(body, 1)

        actions = QHBoxLayout()
        actions.addWidget(generate_button)
        actions.addWidget(open_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择 Issue Package 输出目录", self.output_edit.text())
        if directory:
            self.output_edit.setText(directory)

    def load_clipboard_text(self) -> None:
        text, formats = read_clipboard_conversation_text()
        if not text.strip():
            QMessageBox.warning(self, "IssuePack", "剪贴板里没有文本。")
            return
        self.chat_edit.setPlainText(text)
        rich = "text/html" in formats
        self.status_label.setText(
            f"已读取剪贴板文本（{'检测到富文本，可恢复图片路径' if rich else '仅检测到纯文本'}），点击“解析聊天”。"
        )

    def _stage_recovered_assets(self) -> int:
        staged = 0
        for message in self._placeholders():
            source = source_asset_for(message)
            if source is None:
                continue
            target = self.session_dir / f"{message.id}{source.suffix.lower() or '.bin'}"
            try:
                shutil.copy2(source, target)
            except OSError:
                continue
            self.captured_assets[message.id] = target
            staged += 1
        return staged

    def parse_chat(self) -> None:
        text = self.chat_edit.toPlainText()
        self.messages = parse_wecom_text(text)
        self.captured_assets.clear()
        auto_count = self._stage_recovered_assets()
        self.refresh_placeholders()
        text_count = sum(message.type == MessageType.TEXT for message in self.messages)
        asset_count = sum(message.type != MessageType.TEXT for message in self.messages)
        if not self.messages:
            self.status_label.setText("没有解析到消息。可以保留实际复制格式，用于扩展解析器。")
        else:
            self.status_label.setText(
                f"解析到 {len(self.messages)} 条事件：文本 {text_count}，附件 {asset_count}；已自动恢复 {auto_count} 个本地附件。"
            )

    def _placeholders(self) -> list[Message]:
        return [message for message in self.messages if message.type in {MessageType.IMAGE, MessageType.FILE}]

    def refresh_placeholders(self) -> None:
        self.placeholder_list.clear()
        placeholders = self._placeholders()
        for message in placeholders:
            captured = message.id in self.captured_assets
            icon = "✓" if captured else "○"
            kind = "图片" if message.type == MessageType.IMAGE else "文件"
            mode = "自动恢复" if captured and message.source_asset_path else ("手动捕获" if captured else "待补充")
            item = QListWidgetItem(f"{icon} {message.id} · {message.time} · {message.sender} · {kind} · {mode}")
            item.setData(Qt.ItemDataRole.UserRole, message.id)
            self.placeholder_list.addItem(item)
        done = len([message for message in placeholders if message.id in self.captured_assets])
        total = len(placeholders)
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done)
        self.capture_button.setEnabled(done < total)

    def capture_next_asset(self) -> None:
        target = next((m for m in self._placeholders() if m.id not in self.captured_assets), None)
        if target is None:
            return
        try:
            captured = capture_clipboard_asset(self.session_dir, target.id, target.type)
        except ClipboardCaptureError as exc:
            QMessageBox.warning(self, "捕获失败", str(exc))
            return
        self.captured_assets[target.id] = captured
        self.refresh_placeholders()
        self.status_label.setText(f"已手动捕获 {target.id}: {captured.name}")

    def generate_package(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "IssuePack", "请先填写 Issue 标题。")
            return
        if not self.messages:
            self.parse_chat()
        if not self.messages:
            QMessageBox.warning(self, "IssuePack", "没有可生成的聊天消息。")
            return

        missing = [m for m in self._placeholders() if m.id not in self.captured_assets and source_asset_for(m) is None]
        if missing:
            answer = QMessageBox.question(
                self,
                "存在未补充附件",
                f"还有 {len(missing)} 个图片/文件没有恢复。仍然生成吗？\n未补充项会保留为明确占位。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            package = build_package(Path(self.output_edit.text()), title, self.messages, self.captured_assets)
        except Exception as exc:
            QMessageBox.critical(self, "生成失败", str(exc))
            return

        self.last_package = package
        self.status_label.setText(f"已生成：{package}")
        QMessageBox.information(self, "IssuePack", f"Issue Package 已生成：\n{package}")

    def open_last_package(self) -> None:
        if self.last_package is None:
            QMessageBox.information(self, "IssuePack", "还没有生成 Issue Package。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.fspath(self.last_package)))


def main() -> int:
    app = QApplication(sys.argv)
    window = IssuePackWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
