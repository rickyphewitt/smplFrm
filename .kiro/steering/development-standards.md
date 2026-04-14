---
title: Development Standards
inclusion: always
---

# Development Standards

## Dependency Management
- **NEVER install packages (pip install, npm install, etc.) without explicit user approval** — always ask first
- Use latest stable versions of all libraries and dependencies
- Leverage Context7 MCP server to verify compatibility before adding dependencies
- Justify each new dependency with clear business or technical value
- Prefer well-maintained libraries with active communities
- Document version constraints in project files
- Remove unused dependencies regularly
- Use lock files to ensure consistent installations across environments

## Code Quality Standards
- When choosing default values or magic numbers, always document the rationale — don't blindly adopt values from issue descriptions without independent justification
- Never create duplicate files with suffixes like `_fixed`, `_clean`, `_backup`, etc.
- Work iteratively on existing files (hooks handle commits automatically)
- Include relevant documentation links in code comments
- Follow language-specific conventions (TypeScript for CDK, Python for Lambda)
- Use meaningful variable and function names
- Keep functions small and focused on single responsibilities
- Implement proper error handling and logging

## Formatting and Linting
- **DO NOT** run formatters or linters on file save — formatting is handled by a pre-commit git hook
- **DO NOT** create or enable Kiro hooks that auto-format or auto-lint on save
- The `.pre-commit-config.yaml` defines all formatting and linting rules; they run automatically at commit time

## File Management
- Maintain clean directory structures
- Use consistent naming conventions across the project
- Avoid temporary or backup files in version control
- Organize code logically by feature or domain
- Keep configuration files at appropriate levels (project vs user)

## Documentation Approach
- Maintain single comprehensive README covering all aspects including deployment
- Reference official sources through MCP servers when available
- Update documentation when upgrading dependencies
- Keep documentation close to relevant code
- Use inline comments for complex business logic
- Document API endpoints and data structures
- Include setup and deployment instructions

## Wiki Maintenance
- The project wiki lives in the `docs/` folder and is synced to the GitHub wiki on push to main
- When user-facing functionality is added or changed, update the relevant wiki page in `docs/`
- Wiki pages to keep in sync:
  - `Settings.md` — documents the settings modal tabs (Display, Images, Library, Presets, Plugins, Tasks, About)
- Add screenshots to `docs/images/` when UI changes are significant
- Update `Home.md` links when new pages are added
- **Before completing any task**, prompt whether documentation updates are needed — this applies to new features, changes to existing features, bug fixes that alter behavior, and new environment variables or configuration options

## Version Control Integration
- Commit frequently with meaningful messages
- Use feature branches for development — one branch per subtask (e.g. `feature/133-plugin-architecture`)
- Always checkout a new branch before starting work on a bug or feature (e.g. `fix/174-image-dimension-bounds`)
- Keep main branch deployable at all times
- Tag releases appropriately
- Use .gitignore to exclude generated files and secrets

## Feature Docs
- Local feature docs live in `docs/features/` and serve as the source of truth during development
- Feature docs are **not committed** to the repo. A parent issue will serve as the history instead of cluttering up the codebase with feature docs
- Update the local feature doc when GitHub issue statuses change (closed, merged, etc.)
- The corresponding parent GitHub issue should be updated to reflect changes in the feature doc

## API Standards
- Never implement PATCH endpoints — always use PUT for updates
- All update operations must send the full resource representation
- Partial updates are not supported by design
- Views must always call into service layer methods — never perform model operations directly in views
- All list endpoints must include pagination (5 per page default)

## Preset Configs
- Preset JSON files live in `src/smplfrm/smplfrm/presets/`
- When fields are added or removed from the `Config` model, update all preset JSON files to include the new fields
- Each preset JSON must define every configurable field on the `Config` model (excluding `name`, `description`, and `is_active`)
- Presets are synced to the database on startup via `ConfigService.sync_presets()`

## Quality Assurance
> All items below are mandatory requirements, not suggestions.

- **ALWAYS** follow Test Driven Development (TDD): write tests before implementing functionality
- **NEVER write production code without first writing a failing test** — this applies to new features, bug fixes, and refactors that change behavior
- Write tests for new functionality
- Run tests before committing changes
- When a regression is found, write a failing test for it before fixing the code
- Never modify a regression test without explaining why — include a comment in the test documenting the original bug and the reason for the change
- Use linting and formatting tools consistently
- Perform code reviews for all changes
- Monitor code coverage and maintain high standards