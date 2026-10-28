# Project Rules

## Git

- Start every new feature or fix on a new branch created from `main`, never on
  top of another feature branch (prefixes: `feature/`, `fix/`, `chore/`).
- Bring `main` up to date with `origin` before branching off, so the new
  branch contains all merged changes:
  `git checkout main && git pull --ff-only origin main && git checkout -b feature/<name>`
- Merge pull requests with a merge commit, not squash or rebase.

## Frontend

See `frontend/AGENTS.md`.
