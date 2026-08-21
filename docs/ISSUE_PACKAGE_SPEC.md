# Issue Package Specification v0.3

IssuePack separates source preservation from the context that a coding agent should normally consume.

## 1. Package structure

```text
<issue-package>/
├── AGENTS.md
├── context.md
├── data/
│   ├── meta.json
│   └── messages.jsonl
├── raw/                    # optional source snapshots
│   ├── manifest.json
│   ├── clipboard-001.txt
│   └── clipboard-001.html
├── assets/
│   ├── i1.jpg
│   ├── i2.png
│   └── f1.docx
└── result.md
```

The layers have different purposes and must not be treated as interchangeable.

## 2. Agent context layer

`context.md` is the default and normally sufficient context for the coding agent.

IssuePack uses a compact transcript optimized for chat-shaped requirements:

```text
# 小程序修改
people:A=春天@微信@微信联系人;B=王挺
date:8/17
13:59:52 A> [img:assets/i1.jpg]
14:12:07 A> 这是之前提出的修改意见，还没改，请一并修改
14:12:32 B> 好的，我统一修改
14:21:00 A> 咱们第一次合作做小程序开发，确实有很多功能和细节需要多次沟通，反复修改，辛苦啦 [img:assets/i2.png]
```

Rules:

- A sender name is declared once and replaced by a short alias in transcript rows.
- When a run of messages shares one date, the date is declared once.
- Adjacent events with the same sender and timestamp may be rendered on one line in `context.md`.
- Images use `[img:assets/iN.ext]`.
- Files use `[file:assets/fN.ext]`.
- Missing media remains explicit as `[img:missing]` or `[file:missing]`.
- The compact view may combine events for token efficiency; exact event boundaries remain in `data/messages.jsonl`.

## 3. Progressive disclosure rule

`AGENTS.md` is generated in every package and defines how a coding agent should navigate the package:

1. Read `context.md` first.
2. Open only assets referenced by requirement lines that matter to the current task.
3. Do not proactively read or summarize `data/` or `raw/`.
4. Read `data/messages.jsonl` only when exact message order or metadata is necessary.
5. Read `raw/` only to resolve a contradiction, verify source fidelity, or recover information missing from higher layers.
6. When falling back to lower layers, inspect the smallest specific file or segment needed instead of bulk-loading the directory.

The goal is to prevent a coding agent from spending context tokens on duplicate representations of the same conversation.

## 4. Normalized data layer

`data/messages.jsonl` is the complete normalized timeline after parsing and any human corrections in IssuePack.

Example:

```jsonl
{"id":"msg-001","time":"8/17 14:12:07","sender":"春天@微信@微信联系人","type":"text","content":"这是之前提出的修改意见，还没改，请一并修改"}
{"id":"msg-002","time":"8/17 14:12:32","sender":"王挺","type":"text","content":"好的，我统一修改"}
{"id":"msg-003","time":"8/17 14:21:00","sender":"春天@微信@微信联系人","type":"image","asset":"assets/i1.png"}
```

This layer is intended for exact lookup and tooling, not default model ingestion.

`data/meta.json` stores package metadata such as schema version, title, creation time, and event count.

## 5. Raw source layer

`raw/` stores original clipboard/source snapshots when available. It is evidence and recovery material, not the normal agent prompt.

Source snapshots are immutable. Human insertion, deletion, reordering, and correction affect the normalized `data/` layer and compact `context.md`; they do not rewrite the original source snapshots.

A package can contain multiple source snapshots when missing conversation segments were pasted later.

## 6. Assets

All media exposed to the agent is copied into `assets/` with short names:

```text
assets/i1.jpg
assets/i2.png
assets/f1.docx
```

Short names reduce repeated path tokens while keeping references understandable.

The normalized data layer retains the event-to-asset binding.

## 7. result.md

`result.md` is derived output and is not requirement evidence.

Recommended sections:

```markdown
# Resolution

## Requirement understood

## Files changed

## Verification

## Remaining uncertainties
```

The agent should write it after completing the task, not read it as source context before starting.

## 8. Design principles

```text
raw source
   ↓
parser + human correction
   ↓
data/messages.jsonl
   ↓
compact context renderer
   ↓
context.md
   ↓
coding agent
```

IssuePack is a context transport and orchestration layer. It does not summarize customer intent with an LLM during package creation.

The default path is deliberately lossy only in representation overhead, not in customer meaning: duplicate sender names, duplicate dates, verbose Markdown headings, and repeated structural keys are removed from the agent-facing view while exact normalized events remain available on demand.

## 9. Privacy

Real packages may contain private customer communication, screenshots, source documents, credentials, or commercially sensitive information. They should remain local or in private storage and must not be committed to the public IssuePack source repository.
