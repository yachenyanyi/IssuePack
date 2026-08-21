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
3. IssuePack lists every detected image/file placeholder in chronological order.
4. Back in WeCom, copy the first corresponding image/file.
5. Click **捕获下一个附件**. Repeat until all placeholders are filled.
6. Enter an Issue title and click **生成 Issue Package**.

The generated package contains `issue.md`, `raw/conversation.json`, copied images/attachments, and a `result.md` template.

## Build Windows executable

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

The executable is generated under:

```text
dist\IssuePack\IssuePack.exe
```

## Why clipboard capture

When WeCom copies a media item on Windows, clients can expose the copied item through standard clipboard file-drop/image formats. IssuePack first tries local file URLs and immediately copies the media into a stable session directory; for images it also supports raw clipboard image data.

## Important limitation

WeCom's copied text format can vary between Windows client versions and message types. The V0 parser is intentionally tolerant, but the fastest way to improve it is to add sanitized samples of the exact copied text format that failed together with a parser regression test.

Do not commit real customer conversations, screenshots, or attachments to this public repository.
