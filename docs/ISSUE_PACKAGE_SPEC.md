# Issue Package Specification

This document defines the stable data boundary between real-world customer communication and coding agents.

## 1. Package boundary

Each customer request, bug, change, or investigation is stored as one isolated Issue Package.

Recommended naming:

```text
YYYY-MM-DD-NNN-short-title/
```

Example:

```text
2026-08-21-001-mobile-home/
```

## 2. Required structure

```text
<issue-package>/
├── issue.md
├── raw/
│   └── conversation.json
├── images/
├── attachments/
└── result.md
```

`images/` and `attachments/` may be empty when the conversation contains no such material.

## 3. Raw events are authoritative

IssuePack must preserve the original communication as much as possible.

The source of truth is `raw/conversation.json`. `issue.md` is a deterministic human/agent-readable rendering of those events.

Do not let an LLM rewrite, summarize, merge, or reinterpret the source conversation during package creation.

## 4. Event format

Minimal event schema:

```json
{
  "issue_id": "2026-08-21-001",
  "source": "wecom-clipboard",
  "events": [
    {
      "id": "msg-001",
      "time": "2026-08-21T10:21:00+08:00",
      "sender": "客户A",
      "type": "text",
      "content": "首页这里再改一下"
    },
    {
      "id": "msg-002",
      "time": "2026-08-21T10:22:00+08:00",
      "sender": "客户A",
      "type": "image",
      "file": "images/msg-002-image.png"
    }
  ]
}
```

Initial event types:

- `text`
- `image`
- `file`
- `video`
- `unknown`

Adapters may preserve additional source metadata under a `meta` object, but the common fields above should remain stable.

## 5. Message/file binding

An attachment should be named using the message/event identifier whenever possible.

Preferred:

```text
images/msg-008-image.png
attachments/msg-021-file.docx
```

Avoid generic numbering when the source event ID is available:

```text
001.png
002.png
```

The stable event ID makes later tracing, evaluation, and repair easier.

## 6. issue.md rendering

`issue.md` should preserve chronological order.

Example:

```markdown
# Issue

## 2026-08-21 10:21 · 客户A

首页这里再改一下

## 2026-08-21 10:22 · 客户A

![msg-002](./images/msg-002-image.png)

## 2026-08-21 10:23 · 客户A

手机上还是太大。
```

Do not add inferred sections such as `Requirement`, `Technical Solution`, or `Affected Files` during package creation.

Those belong to agent output, not source context.

## 7. result.md

`result.md` is not part of the original evidence. It is generated after an agent completes the task.

Recommended fields:

```markdown
# Resolution

## Requirement understood

## Relevant implementation

## Files changed

## Changes

## Verification

## Remaining uncertainty

## Related commit / PR
```

This separation is important:

```text
issue.md  = source context
result.md = derived agent output
```

## 8. Privacy

Real Issue Packages may contain private customer information, screenshots, source documents, credentials, or commercially sensitive content.

The IssuePack source repository may be public, but real packages should default to local or private storage and should be excluded from Git by default.

## 9. Adapter rule

Source-specific collectors must not define the Issue Package format.

Examples:

```text
WeComClipboardAdapter ─┐
WeComDesktopAdapter   ├─> Raw Events -> Renderer -> Issue Package
FutureAPIAdapter      ┘
```

This allows collection mechanisms to change without changing the package contract.

## 10. Context principle

IssuePack is a context transport layer, not a requirement reasoning layer.

Its job is:

```text
find + capture + preserve + bind + render
```

The coding agent's job is:

```text
inspect repository + interpret context + implement + verify
```
