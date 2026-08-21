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
3. IssuePack reads both plain text and rich clipboard data, restoring local `file:///...` image paths when possible.
4. Review the parsed timeline on the right. Messages can be edited, inserted, reordered, or deleted.
5. If a whole conversation segment is missing, copy that segment in WeCom and use **剪贴板前插 / 剪贴板后插**.
6. Use manual attachment capture only for media that could not be restored automatically.
7. Enter an Issue title and click **生成 Issue Package**.

The right-side timeline is the normalized source used to generate the agent-facing package. Re-parsing the left-side source replaces manual timeline edits and therefore asks for confirmation first.

## Generated package

```text
<issue-package>/
├── AGENTS.md
├── context.md
├── data/
│   ├── meta.json
│   └── messages.jsonl
├── raw/
│   ├── manifest.json
│   ├── clipboard-001.txt
│   └── clipboard-001.html
├── assets/
│   ├── i1.jpg
│   └── f1.docx
└── result.md
```

`context.md` is the compact default context for the coding agent. Package `AGENTS.md` explicitly instructs the agent not to bulk-read `data/`, `raw/`, or every asset. Exact normalized events and original clipboard snapshots remain available only as fallback layers.

## Compact context format

```text
# 小程序修改
people:A=春天@微信@微信联系人;B=王挺
date:8/17
14:12:07 A> 这是之前提出的修改意见，还没改，请一并修改
14:12:32 B> 好的，我统一修改
14:21:00 A> 辛苦啦 [img:assets/i1.png]
```

This removes repeated sender names, repeated dates, verbose Markdown headings, and long media identifiers from the model's normal input while preserving exact data separately.

## Timeline editing

The timeline supports:

- **保存修改** — edit sender, time, type, and content of the selected row.
- **前插一条 / 后插一条** — insert a blank text message near the selected row.
- **剪贴板前插 / 剪贴板后插** — parse a copied WeCom conversation segment and insert multiple messages at once.
- **上移 / 下移** — reorder the selected message.
- **删除** — remove a message from the final package.

After insert, reorder, or delete operations, IssuePack regenerates `msg-001`, `msg-002`, ... IDs from the final timeline order while keeping captured media bound to the correct message.

WeCom lines that contain ordinary text followed by a rich image reference, for example:

```text
辛苦啦[image](file:///C:/Users/User/AppData/Local/Temp/example.png)
```

are split into a text event followed by an image event for editing. The compact renderer may merge adjacent same-sender/same-time events back onto one line in `context.md` to save tokens.

## Raw source snapshots

When the conversation is read from the clipboard, IssuePack stores the original plain-text and HTML clipboard flavors in `raw/`. If a missing segment is later inserted from the clipboard, that segment is stored as another raw snapshot.

Human edits affect the normalized timeline and `context.md`; they do not rewrite the original source snapshots.

## Build Windows executable

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

The executable is generated under:

```text
dist\IssuePack\IssuePack.exe
```

GitHub Actions also builds the Windows package automatically and uploads `IssuePack-windows-x64` as an artifact.

## Important limitation

WeCom's copied text and rich clipboard formats can vary between Windows client versions and message types. The parser is intentionally tolerant. When a new format fails, add a sanitized sample and regression test instead of adding LLM-based preprocessing.

Do not commit real customer conversations, screenshots, raw clipboard snapshots, or attachments to this public repository.
