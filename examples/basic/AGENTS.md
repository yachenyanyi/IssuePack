# IssuePack agent instructions

- Use `context.md` as the only default entrypoint for this issue package.
- Do not proactively open, enumerate, summarize, or ingest `data/` or `raw/`.
- Open only assets explicitly referenced by the relevant lines in `context.md`; do not bulk-read every asset.
- Read `data/messages.jsonl` only when exact message order, metadata, or an omitted detail is necessary to resolve the task.
- Read `raw/` only to resolve a contradiction, verify source fidelity, or recover information unavailable from `context.md` and `data/`; inspect the smallest specific source file needed.
- `result.md` is agent output, not source evidence.
