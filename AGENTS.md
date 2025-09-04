# Repository Guidelines

## Project Structure & Module Organization
- Source: `src/` for application code; split by feature/domain.
- Tests: `tests/` mirrors `src/` (e.g., `src/api/user.ts` → `tests/api/user.spec.ts`).
- Scripts: `scripts/` for repeatable tasks (`dev`, `test`, `lint`, `format`).
- Docs: `docs/` for architecture notes and ADRs; examples in `examples/`.
- Config: root-level dotfiles (`.editorconfig`, linters), environment samples in `.env.example`.

## Build, Test, and Development Commands
Use script shims to keep workflows consistent across languages:
- `./scripts/dev`: start local development server or watcher.
- `./scripts/test`: run the test suite with coverage.
- `./scripts/lint`: run linters and static analysis.
- `./scripts/format`: apply auto-formatting.
Examples:
- Node: `npm run dev`, `npm test`, `npm run lint`.
- Python: `pytest -q`, `ruff check .`, `black .`.

## Coding Style & Naming Conventions
- Indentation: 2 spaces for JSON/YAML; otherwise follow language norms (Python 4 spaces).
- Files/dirs: kebab-case for folders and non-code assets; code files follow language norms (Python `snake_case.py`, TypeScript `CamelCase.ts` for types, otherwise `kebab-case.ts`).
- Imports: prefer absolute paths via module aliasing when supported.
- Formatting/Linting (adopt per language):
  - JavaScript/TypeScript: Prettier + ESLint.
  - Python: Black + Ruff.
  - Go: `gofmt` + `golangci-lint`.
  - Rust: `rustfmt` + `clippy`.

## Testing Guidelines
- Frameworks: Jest/Vitest (JS/TS), Pytest (Python), `go test`, Cargo test (Rust).
- Structure: unit tests colocated in `tests/` mirroring `src/`.
- Naming: `*.spec.ts`, `test_*.py`, `*_test.go`.
- Coverage: target ≥ 80% lines; add regression tests for every bug fix.
- Run: `./scripts/test` or language-specific commands above.

## Commit & Pull Request Guidelines
- Commits: follow Conventional Commits (e.g., `feat(api): add token refresh`).
- Scope small, atomic changes; include rationale in the body when non-trivial.
- PRs: clear description, linked issues (`Closes #123`), screenshots for UI, and steps to verify.
- Checks: ensure `lint`, `format`, and `test` pass locally before requesting review.

## Security & Configuration Tips
- Never commit secrets; use `.env` locally and provide `.env.example`.
- Validate inputs at boundaries; treat all external data as untrusted.
- Review dependency updates for license and security implications.
