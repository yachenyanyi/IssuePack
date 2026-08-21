# Windows V0

IssuePack V0 is a local Windows desktop utility implemented with Python 3.11 + PySide6.

## Run from source

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
issuepack
```

## Current workflow

1. In WeCom, select and copy the relevant conversation.
2. Click **读取剪贴板**, then **解析聊天**.
3. IssuePack builds an editable message timeline and automatically restores local image/file paths found in WeCom rich clipboard data.
4. Review the timeline before generation. You can edit sender/time/content/type, insert rows, reorder rows, or delete rows.
5. If an entire chat segment was missed, copy that segment again in WeCom, select the insertion point, and use **剪贴板前插** or **剪贴板后插**. The whole segment is parsed and inserted at once, including recoverable media.
6. For media that cannot be restored automatically, select the corresponding image/file row, copy the media in WeCom, and click **捕获选中/下一个未解析附件**.
7. Enter an Issue title and click **生成 Issue Package**.

The right-side timeline is the final source used to generate the Issue Package. Re-parsing the left-side raw conversation replaces manual timeline edits and therefore asks for confirmation first.

The generated package contains `issue.md`, `raw/conversation.json`, copied images/attachments, and a `result.md` template.

## Timeline editing

The timeline supports:

- **保存修改** — edit sender, time, type, and content of the selected row.
- **前插一条 / 后插一条** — insert a blank text message near the selected row.
- **剪贴板前插 / 剪贴板后插** — parse a copied WeCom conversation segment and insert multiple messages at once.
- **上移 / 下移** — reorder the selected message.
- **删除** — remove a message from the final package.

After insert, reorder, or delete operations, IssuePack regenerates `msg-001`, `msg-002`, ... IDs from the final timeline order while keeping already captured media bound to the correct message.

WeCom lines that contain ordinary text followed by a rich image reference, for example:

```text
辛苦啦[image](file:///C:/Users/User/AppData/Local/Temp/example.png)
```

are split into a text event followed by an image event so both can be edited and reordered independently.

## Build Windows executable

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

The executable is generated under:

```text
dist\IssuePack\IssuePack.exe
```

GitHub Actions also builds the Windows package automatically and uploads `IssuePack-windows-x64` as a workflow artifact.

## Why rich clipboard capture

When WeCom copies a conversation on Windows, the clipboard can contain both plain text and HTML/rich content. The plain text is useful for sender/time/message order, while the rich content can expose original local `file:///...` media paths. IssuePack combines both and copies recoverable media into a stable session directory immediately.

Manual clipboard capture remains a fallback for message types where WeCom does not provide a usable local path.

## Important limitation

WeCom's copied text/rich clipboard format can vary between Windows client versions and message types. The parser is intentionally tolerant, and sanitized real-world samples should be added as regression tests whenever a format is not handled correctly.

Do not commit real customer conversations, screenshots, or attachments to this public repository.
