# Project Rules

## Git

- Start every new feature or fix on a new branch created from an up-to-date
  `main`, never on top of another feature branch:
  `git fetch origin && git checkout -b feature/<name> origin/main`
  (prefixes: `feature/`, `fix/`, `chore/`).
- Merge pull requests with a merge commit, not squash or rebase.

## Frontend

See `frontend/AGENTS.md`.
