# Git Best Practices

## Commit Messages
- Use [Conventional Commits](https://www.conventionalcommits.org/) format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`
- Scope is optional but encouraged for clarity (e.g., `feat(api):`, `fix(auth):`)
- Keep title under 72 characters
- Use imperative mood ("Add feature" not "Added feature")
- Body: concise bulleted list of what was done
- Do not include test pass/fail rates in commit messages

## Branching
- Use feature branches for new development
- Keep main/master branch stable and deployable
- Use descriptive branch names (feature/user-auth, fix/login-bug)
- Delete merged branches to keep repository clean

## Workflow
- Pull latest changes before starting work
- Commit frequently with logical chunks during development
- Before pushing: squash/amend local commits into a single commit per feature/fix
- Review code before merging (pull requests)

## Repository Management
- Use .gitignore to exclude build artifacts and secrets
- Keep repository size manageable (use Git LFS for large files)
- Tag releases with semantic versioning
- Document branching strategy in README

## Security
- Never commit secrets, API keys, or passwords
- Use environment variables for configuration
- Review commits for sensitive information
- Use signed commits when possible
