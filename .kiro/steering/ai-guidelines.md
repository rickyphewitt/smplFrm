---
title: AI Guidelines Pattern
inclusion: always
---

This project uses a three-layer AI guidelines pattern:

1. **Knowledge Layer** (`ai/`): Tool-agnostic markdown — the single source of truth.
2. **Adapter Layer** (this directory + `.claude/rules/`): Thin pointers that load knowledge files.
3. **Personal Layer** (`.kiro/steering/local/`, `CLAUDE.local.md`): Gitignored personal overrides.

When updating guidelines, always edit the file in `ai/`. Never put content directly in adapter files.
