# AI Guidelines

This project uses a **three-layer pattern** to manage AI coding guidelines across multiple tools without duplicating content.

## The Three Layers

### 1. Knowledge Layer (`ai/`)

Tool-agnostic markdown files that serve as the **single source of truth** for all project guidelines. These files:

- Contain no YAML frontmatter or tool-specific syntax
- Are readable by any AI tool or human
- Start with an H1 heading and are self-contained
- Live at the project root under `ai/`

### 2. Adapter Layer (tool-specific pointers)

Thin 3–5 line files in each tool's native configuration directory. Each adapter:

- Uses the tool's native frontmatter format for scoping (always-on, file-match, etc.)
- Contains only a short instruction to read and apply the corresponding knowledge file
- Never duplicates the actual guideline content

### 3. Personal Layer (gitignored overrides)

Per-developer override files that are gitignored so they never pollute the shared repo:

- **Kiro**: `.kiro/steering/local/*.md`
- **Claude Code**: `CLAUDE.local.md`

These load after the shared adapters and can extend or override guidelines for individual workflows.

---

## Currently Supported AI Tools

| Tool | Adapter Location | Meta-Adapter |
|------|-----------------|--------------|
| **Kiro** | `.kiro/steering/<topic>.md` | `.kiro/steering/ai-guidelines.md` |
| **Claude Code** | `.claude/rules/<topic>.md` | `CLAUDE.md` (project root) |

---

## Adding a New Guideline Topic

1. Create `ai/<topic>.md` with an H1 heading and the guideline content (no frontmatter).
2. Create a Kiro adapter at `.kiro/steering/<topic>.md` with appropriate `inclusion` frontmatter and a pointer to the knowledge file.
3. Create a Claude adapter at `.claude/rules/<topic>.md` with appropriate `alwaysApply`/`globs` frontmatter and a pointer to the knowledge file.
4. Done — all tools will pick up the new topic automatically.

---

## Onboarding a New AI Agent

Follow these steps to add support for any new AI coding tool (Cursor, Windsurf, Copilot, etc.):

### Step 1: Identify the tool's rules directory and file format

Find where the tool reads its configuration files and what extension it expects.

Examples:
- Cursor: `.cursor/rules/*.mdc`
- Windsurf: `.windsurf/rules/*.md`
- GitHub Copilot: `.github/copilot-instructions.md`

### Step 2: Identify the tool's frontmatter fields for scoping

Determine how the tool scopes rules to specific files or makes them always-active.

Examples:
- Cursor: `alwaysApply: true` or `globs: "*.py"`
- Windsurf: `fileMatchPattern: "*.ts"` or `trigger: always`

### Step 3: Create the adapter directory

```bash
mkdir -p .<tool>/rules/
```

### Step 4: Create a thin adapter for each knowledge file

For each `ai/<topic>.md`, create a corresponding adapter in the tool's directory with:
- The tool's native frontmatter for scoping
- A single instruction line pointing to the knowledge file

### Step 5: Create a meta-adapter

Create a special adapter that teaches the agent about the three-layer pattern. It should explain:
- Where knowledge files live (`ai/`)
- That `ai/<topic>.md` is the single source of truth
- That the agent should modify only knowledge files when updating guidelines

### Step 6: Add the tool's personal override location to `.gitignore`

```gitignore
# Personal AI overrides — <Tool Name>
.<tool>/rules/local/
```

### Step 7: Update this README

Add the new tool to the "Currently Supported AI Tools" table above.

---

## Concrete Example: Adding Cursor Support

### Directory structure

```
.cursor/
└── rules/
    ├── architecture.mdc
    ├── python-best-practices.mdc
    ├── docker-best-practices.mdc
    ├── ...
    └── ai-guidelines.mdc        ← meta-adapter
```

### Always-on adapter (`.cursor/rules/architecture.mdc`)

```markdown
---
alwaysApply: true
---

Read and apply the rules from ai/architecture.md.
```

### File-scoped adapter (`.cursor/rules/python-best-practices.mdc`)

```markdown
---
globs: "*.py"
---

Read and apply the rules from ai/python-best-practices.md.
```

### Meta-adapter (`.cursor/rules/ai-guidelines.mdc`)

```markdown
---
alwaysApply: true
---

This project uses a three-layer AI guidelines pattern:

1. **Knowledge Layer** (`ai/`): Tool-agnostic markdown — the single source of truth.
2. **Adapter Layer** (this directory): Thin pointers that load knowledge files.
3. **Personal Layer** (`.cursor/rules/local/`): Gitignored personal overrides.

When updating guidelines, always edit the file in `ai/`. Never put content directly in adapter files.
```

### Gitignore entry

```gitignore
# Personal AI overrides — Cursor
.cursor/rules/local/
```

---

## Knowledge Files

| File | Topic |
|------|-------|
| `ai/architecture.md` | Project architecture and structure |
| `ai/development-standards.md` | General development standards |
| `ai/docker-best-practices.md` | Docker and container practices |
| `ai/git-best-practices.md` | Git workflow and conventions |
| `ai/python-best-practices.md` | Python coding standards |
| `ai/security-best-practices.md` | Security guidelines |
| `ai/testing-best-practices.md` | Testing practices and commands |
