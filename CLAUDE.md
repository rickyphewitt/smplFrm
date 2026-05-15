# Project: smplFrm

## AI Guidelines Pattern

This project uses a three-layer AI guidelines pattern:

1. **Knowledge Layer** (`ai/`): Tool-agnostic markdown — the single source of truth.
2. **Adapter Layer** (`.claude/rules/`): Thin pointers that load knowledge files.
3. **Personal Layer** (`CLAUDE.local.md`): Gitignored personal overrides.

When updating guidelines, always edit the file in `ai/`. Never put content directly in adapter files or this file.

## Project Overview

smplFrm is a Django application that serves a digital photo frame UI. See `ai/architecture.md` for full details.
