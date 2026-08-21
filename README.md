# IssuePack

IssuePack turns messy real-world customer communication into a complete, traceable context package that coding agents can consume directly.

The first target workflow is software outsourcing / maintenance work where requirements arrive through chat messages, screenshots, images, documents, and files rather than clean GitHub issues.

## Current status

A Windows V0 is implemented with Python 3.11 + PySide6. It can parse copied WeCom chat text and rich clipboard data, automatically recover local image/file paths when available, let the user correct the parsed message timeline, and generate a local Issue Package.

See [Windows V0 usage](docs/WINDOWS_V0.md) and [Issue Package Specification](docs/ISSUE_PACKAGE_SPEC.md).

## Core idea

IssuePack does **not** try to understand or summarize the customer's requirement before handing it to the coding agent.

Its responsibility is to preserve evidence, build a human-correctable timeline, and render a compact agent-facing context:

```text
Customer chat + screenshots + files
        ↓
     IssuePack
        ↓
 editable normalized timeline
        ↓
 compact context.md
        ↓
Codex / coding agent
        ↓
open deeper data only when needed
        ↓
code / test / result
```

## Design principles

1. **Raw context first** — preserve original source material when available.
2. **No premature summarization** — IssuePack does not use an LLM to rewrite customer meaning during package creation.
3. **One issue, one package** — every customer problem has an isolated context boundary.
4. **Multimodal by default** — images and files are first-class context.
5. **Human-correctable** — parsed messages can be inserted, edited, reordered, and deleted before generation.
6. **Progressive disclosure** — agents read the compact context first and descend into exact/raw data only when necessary.
7. **Token-conscious** — repeated dates, sender names, verbose Markdown headings, and long asset names are removed from the default agent view.
8. **Local-first for customer data** — real customer conversations and attachments should not be committed to this repository.

## Issue Package v0.3

```text
2026-08-21-001-mobile-home/
├── AGENTS.md
├── context.md
├── data/
│   ├── meta.json
│   └── messages.jsonl
├── raw/                    # optional source snapshots
├── assets/
│   ├── i1.jpg
│   ├── i2.png
│   └── f1.docx
└── result.md
```

The coding agent should normally consume only `context.md` plus the specific referenced assets relevant to the task. `AGENTS.md` explicitly tells the agent not to bulk-read `data/`, `raw/`, or all assets.

Example compact context:

```text
# 小程序修改
people:A=春天@微信@微信联系人;B=王挺
date:8/17
13:59:52 A> [img:assets/i1.jpg]
14:12:07 A> 这是之前提出的修改意见，还没改，请一并修改
14:12:32 B> 好的，我统一修改
14:21:00 A> 咱们第一次合作做小程序开发，确实有很多功能和细节需要多次沟通，反复修改，辛苦啦 [img:assets/i2.png]
```

Exact event boundaries remain in `data/messages.jsonl` for on-demand lookup.

## Windows V0 workflow

```text
1. Copy selected WeCom chat messages
2. IssuePack reads plain text + rich clipboard data
3. Parse date / sender / text / local media paths
4. Automatically recover images/files when possible
5. Review and edit the message timeline
6. Insert missing rows or paste an entire missing chat segment into the middle
7. Reorder/delete messages as needed
8. Generate the Issue Package
9. Coding agent starts from context.md and opens deeper files only when required
```

Run from source:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
issuepack
```

Build an executable:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

GitHub Actions also builds the Windows package automatically and uploads `IssuePack-windows-x64` as a workflow artifact.

## Roadmap

### V0 — Package builder

- [x] Parse copied WeCom conversation text and rich clipboard data
- [x] Recover local image/file paths when available
- [x] Manual clipboard fallback for unresolved media
- [x] Editable message timeline
- [x] Insert missing chat segments from clipboard
- [x] Reorder/delete parsed messages while keeping attachment bindings
- [x] Generate compact `context.md`
- [x] Generate normalized `data/messages.jsonl`
- [x] Generate package-scoped `AGENTS.md` for progressive disclosure

### V1 — Desktop utility

- [ ] Windows tray application
- [ ] Global shortcut
- [ ] Project selection
- [ ] Faster timeline editing / keyboard shortcuts
- [x] One-click package creation
- [ ] Open / hand off package to Codex

### V2 — WeCom adapter

- Windows UI Automation adapter
- Semi-automatic media capture
- Preserve adapter boundaries so WeCom UI changes do not affect the package format

### V3 — Context orchestration

- Related historical issue retrieval
- Project memory
- Git history retrieval
- Context indexes without replacing raw material

### V4 — Agent evaluation

- Re-run old issue packages against newer agents
- Measure compact-context token savings against task correctness
- Track first-pass success rate, human intervention, rework, tests, and regressions

## Privacy

Real customer conversations, screenshots, and attachments should remain local or in private storage. The repository `.gitignore` intentionally excludes common runtime Issue Package directories.
