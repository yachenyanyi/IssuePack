from __future__ import annotations

import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
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

from .clipboard import (
    ClipboardCaptureError,
    ClipboardConversation,
    capture_clipboard_asset,
    read_clipboard_conversation_payload,
)
from .models import Message, MessageType
from .package_builder import build_package, source_asset_for
from .parser import parse_wecom_text
from .timeline import reindex_messages


class IssuePackWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IssuePack V0")
        self.resize(1320, 840)

        self.messages: list[Message] = []
        self.captured_assets: dict[str, Path] = {}
        self.raw_snapshots: list[dict[str, object]] = []
        self.session_dir = Path(tempfile.mkdtemp(prefix="issuepack-session-"))
        self.last_package: Path | None = None
        self.timeline_dirty = False

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

        self.message_list = QListWidget()
        self.message_list.setMinimumWidth(470)
        self.message_list.currentRowChanged.connect(self.load_selected_message)

        self.sender_edit = QLineEdit()
        self.time_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItem("文本", MessageType.TEXT.value)
        self.type_combo.addItem("图片", MessageType.IMAGE.value)
        self.type_combo.addItem("文件", MessageType.FILE.value)
        self.content_edit = QPlainTextEdit()
        self.content_edit.setPlaceholderText("当前消息内容；图片/文件消息可保留说明文字。")
        self.content_edit.setMaximumHeight(110)

        save_button = QPushButton("保存修改")
        save_button.clicked.connect(self.save_selected_message)
        insert_before_button = QPushButton("前插一条")
        insert_before_button.clicked.connect(lambda: self.insert_message(before=True))
        insert_after_button = QPushButton("后插一条")
        insert_after_button.clicked.connect(lambda: self.insert_message(before=False))
        move_up_button = QPushButton("上移")
        move_up_button.clicked.connect(lambda: self.move_selected_message(-1))
        move_down_button = QPushButton("下移")
        move_down_button.clicked.connect(lambda: self.move_selected_message(1))
        delete_button = QPushButton("删除")
        delete_button.clicked.connect(self.delete_selected_message)
        clear_editor_button = QPushButton("清空编辑区")
        clear_editor_button.clicked.connect(self.clear_message_editor)
        clipboard_before_button = QPushButton("剪贴板前插")
        clipboard_before_button.clicked.connect(lambda: self.insert_clipboard_messages(before=True))
        clipboard_after_button = QPushButton("剪贴板后插")
        clipboard_after_button.clicked.connect(lambda: self.insert_clipboard_messages(before=False))

        self.capture_button = QPushButton("捕获选中/下一个未解析附件")
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
        left.addWidget(QLabel("企业微信聊天原文（重新解析会覆盖右侧人工编辑）"))
        left.addWidget(self.chat_edit, 1)
        left_actions = QHBoxLayout()
        left_actions.addWidget(paste_button)
        left_actions.addWidget(parse_button)
        left.addLayout(left_actions)
        body.addLayout(left, 3)

        right = QVBoxLayout()
        right.addWidget(QLabel("消息时间线（这里的顺序和内容将用于最终 Issue Package）"))
        right.addWidget(self.message_list, 2)

        editor = QGroupBox("编辑选中消息")
        editor_layout = QGridLayout(editor)
        editor_layout.addWidget(QLabel("发送人"), 0, 0)
        editor_layout.addWidget(self.sender_edit, 0, 1)
        editor_layout.addWidget(QLabel("时间"), 1, 0)
        editor_layout.addWidget(self.time_edit, 1, 1)
        editor_layout.addWidget(QLabel("类型"), 2, 0)
        editor_layout.addWidget(self.type_combo, 2, 1)
        editor_layout.addWidget(QLabel("内容"), 3, 0, Qt.AlignmentFlag.AlignTop)
        editor_layout.addWidget(self.content_edit, 3, 1)
        right.addWidget(editor)

        edit_actions_1 = QHBoxLayout()
        edit_actions_1.addWidget(save_button)
        edit_actions_1.addWidget(insert_before_button)
        edit_actions_1.addWidget(insert_after_button)
        right.addLayout(edit_actions_1)

        edit_actions_2 = QHBoxLayout()
        edit_actions_2.addWidget(move_up_button)
        edit_actions_2.addWidget(move_down_button)
        edit_actions_2.addWidget(delete_button)
        edit_actions_2.addWidget(clear_editor_button)
        right.addLayout(edit_actions_2)

        clipboard_actions = QHBoxLayout()
        clipboard_actions.addWidget(clipboard_before_button)
        clipboard_actions.addWidget(clipboard_after_button)
        right.addLayout(clipboard_actions)

        right.addWidget(QLabel("附件（优先自动恢复；选中未解析图片/文件后可手动捕获）"))
        right.addWidget(self.capture_button)
        right.addWidget(self.progress)
        body.addLayout(right, 2)
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

    @staticmethod
    def _raw_snapshot(payload: ClipboardConversation, purpose: str) -> dict[str, object]:
        return {
            "purpose": purpose,
            "plain_text": payload.plain_text,
            "html_text": payload.html_text,
            "formats": payload.formats,
        }

    def load_clipboard_text(self) -> None:
        payload = read_clipboard_conversation_payload()
        text = payload.enriched_text
        if not text.strip():
            QMessageBox.warning(self, "IssuePack", "剪贴板里没有文本。")
            return
        self.chat_edit.setPlainText(text)
        self.raw_snapshots = [self._raw_snapshot(payload, "initial")]
        rich = "text/html" in payload.formats
        self.status_label.setText(
            f"已读取剪贴板文本（{'检测到富文本，可恢复图片路径' if rich else '仅检测到纯文本'}），点击“解析聊天”。"
        )

    def _placeholders(self) -> list[Message]:
        return [message for message in self.messages if message.type in {MessageType.IMAGE, MessageType.FILE}]

    def _stage_recovered_assets(self) -> int:
        staged = 0
        for message in self._placeholders():
            if message.id in self.captured_assets:
                continue
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
        if self.timeline_dirty and self.messages:
            answer = QMessageBox.question(
                self,
                "覆盖人工编辑？",
                "重新解析左侧聊天原文会覆盖右侧已经手动插入、删除、排序或修改的记录。继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        text = self.chat_edit.toPlainText()
        if text.strip() and not self.raw_snapshots:
            self.raw_snapshots = [
                {
                    "purpose": "manual-source",
                    "plain_text": text,
                    "html_text": "",
                    "formats": ["text/plain"],
                }
            ]
        self.messages = parse_wecom_text(text)
        self.captured_assets.clear()
        auto_count = self._stage_recovered_assets()
        self.timeline_dirty = False
        self.refresh_timeline(0 if self.messages else None)
        text_count = sum(message.type == MessageType.TEXT for message in self.messages)
        asset_count = sum(message.type != MessageType.TEXT for message in self.messages)
        if not self.messages:
            self.status_label.setText("没有解析到消息。可以保留实际复制格式，用于扩展解析器。")
        else:
            self.status_label.setText(
                f"解析到 {len(self.messages)} 条事件：文本 {text_count}，附件 {asset_count}；已自动恢复 {auto_count} 个本地附件。"
            )

    def _message_summary(self, message: Message) -> str:
        if message.type == MessageType.TEXT:
            preview = " ".join(message.content.split())
            if len(preview) > 54:
                preview = preview[:51] + "..."
            return f"文本 · {preview or '（空）'}"

        captured = message.id in self.captured_assets
        kind = "图片" if message.type == MessageType.IMAGE else "文件"
        if captured and message.source_asset_path:
            mode = "自动恢复"
        elif captured:
            mode = "手动捕获"
        else:
            mode = "待补充"
        return f"{kind} · {mode}"

    def refresh_timeline(self, selected_index: int | None = None) -> None:
        if selected_index is None:
            selected_index = self.message_list.currentRow()

        self.message_list.clear()
        for message in self.messages:
            item = QListWidgetItem(
                f"{message.id} · {message.time or '无时间'} · {message.sender or 'Unknown'} · {self._message_summary(message)}"
            )
            item.setData(Qt.ItemDataRole.UserRole, message.id)
            self.message_list.addItem(item)

        if self.messages:
            row = selected_index if selected_index is not None and selected_index >= 0 else 0
            row = min(row, len(self.messages) - 1)
            self.message_list.setCurrentRow(row)
        else:
            self.clear_message_editor()

        self.refresh_asset_progress()

    def refresh_asset_progress(self) -> None:
        placeholders = self._placeholders()
        done = len([message for message in placeholders if message.id in self.captured_assets])
        total = len(placeholders)
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done)
        self.capture_button.setEnabled(done < total)

    def load_selected_message(self, row: int) -> None:
        if row < 0 or row >= len(self.messages):
            return
        message = self.messages[row]
        self.sender_edit.setText(message.sender)
        self.time_edit.setText(message.time)
        combo_index = self.type_combo.findData(message.type.value)
        if combo_index >= 0:
            self.type_combo.setCurrentIndex(combo_index)
        self.content_edit.setPlainText(message.content)

    def clear_message_editor(self) -> None:
        self.sender_edit.clear()
        self.time_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.content_edit.clear()

    def _selected_index(self) -> int | None:
        row = self.message_list.currentRow()
        if 0 <= row < len(self.messages):
            return row
        return None

    def _reindex_timeline(self) -> None:
        self.captured_assets = reindex_messages(self.messages, self.captured_assets)

    def save_selected_message(self) -> None:
        index = self._selected_index()
        if index is None:
            QMessageBox.information(self, "IssuePack", "请先在时间线中选择一条消息。")
            return

        message = self.messages[index]
        new_type = MessageType(self.type_combo.currentData())
        if new_type != message.type:
            self.captured_assets.pop(message.id, None)
            message.source_asset_path = None
            message.asset_path = None

        message.sender = self.sender_edit.text().strip() or "Unknown"
        message.time = self.time_edit.text().strip()
        message.type = new_type
        message.content = self.content_edit.toPlainText()
        self.timeline_dirty = True
        self.refresh_timeline(index)
        self.status_label.setText(f"已修改 {message.id}。最终生成将使用右侧时间线内容。")

    def insert_message(self, before: bool) -> None:
        selected = self._selected_index()
        if selected is None:
            insert_at = 0 if before else len(self.messages)
            sender = self.sender_edit.text().strip() or "Unknown"
            time = self.time_edit.text().strip()
        else:
            insert_at = selected if before else selected + 1
            anchor = self.messages[selected]
            sender = anchor.sender
            time = anchor.time

        self.messages.insert(
            insert_at,
            Message(
                id=f"insert-{uuid.uuid4().hex}",
                sender=sender,
                time=time,
                type=MessageType.TEXT,
                content="",
            ),
        )
        self._reindex_timeline()
        self.timeline_dirty = True
        self.refresh_timeline(insert_at)
        self.content_edit.setFocus()
        self.status_label.setText("已插入一条空白文本记录。填写右侧编辑区后点击“保存修改”。")

    def insert_clipboard_messages(self, before: bool) -> None:
        payload = read_clipboard_conversation_payload()
        text = payload.enriched_text
        if not text.strip():
            QMessageBox.warning(self, "IssuePack", "剪贴板里没有可插入的聊天文本。")
            return

        inserted = parse_wecom_text(text)
        if not inserted:
            QMessageBox.warning(self, "IssuePack", "没有从剪贴板解析到可插入的聊天记录。")
            return

        for message in inserted:
            message.id = f"insert-{uuid.uuid4().hex}"

        selected = self._selected_index()
        if selected is None:
            insert_at = 0 if before else len(self.messages)
        else:
            insert_at = selected if before else selected + 1

        self.messages[insert_at:insert_at] = inserted
        self.raw_snapshots.append(self._raw_snapshot(payload, "insert-before" if before else "insert-after"))
        self._reindex_timeline()
        auto_count = self._stage_recovered_assets()
        self.timeline_dirty = True
        self.refresh_timeline(insert_at)
        self.status_label.setText(
            f"已从剪贴板插入 {len(inserted)} 条消息，其中自动恢复 {auto_count} 个附件。可继续调整顺序或编辑。"
        )

    def move_selected_message(self, delta: int) -> None:
        index = self._selected_index()
        if index is None:
            return
        target = index + delta
        if target < 0 or target >= len(self.messages):
            return

        message = self.messages.pop(index)
        self.messages.insert(target, message)
        self._reindex_timeline()
        self.timeline_dirty = True
        self.refresh_timeline(target)
        self.status_label.setText(f"已调整消息顺序：当前为 {self.messages[target].id}。")

    def delete_selected_message(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        message = self.messages[index]
        answer = QMessageBox.question(
            self,
            "删除消息？",
            f"确定删除 {message.id} · {message.sender} · {message.time} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.captured_assets.pop(message.id, None)
        self.messages.pop(index)
        self._reindex_timeline()
        self.timeline_dirty = True
        next_index = min(index, len(self.messages) - 1) if self.messages else None
        self.refresh_timeline(next_index)
        self.status_label.setText("已删除消息并重新编号，其他附件绑定已自动保持。")

    def capture_next_asset(self) -> None:
        target: Message | None = None
        selected = self._selected_index()
        if selected is not None:
            selected_message = self.messages[selected]
            if (
                selected_message.type in {MessageType.IMAGE, MessageType.FILE}
                and selected_message.id not in self.captured_assets
            ):
                target = selected_message

        if target is None:
            target = next((m for m in self._placeholders() if m.id not in self.captured_assets), None)
        if target is None:
            return

        try:
            captured = capture_clipboard_asset(self.session_dir, target.id, target.type)
        except ClipboardCaptureError as exc:
            QMessageBox.warning(self, "捕获失败", str(exc))
            return
        self.captured_assets[target.id] = captured
        self.timeline_dirty = True
        selected_index = self.messages.index(target)
        self.refresh_timeline(selected_index)
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
            package = build_package(
                Path(self.output_edit.text()),
                title,
                self.messages,
                self.captured_assets,
                raw_snapshots=self.raw_snapshots,
            )
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
