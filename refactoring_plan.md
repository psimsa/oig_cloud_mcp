# Refactoring Plan: Top-level layout and migration

Summary
- Reorganize code into `src/`, move CLI/launch scripts into `bin/`, relocate test fixtures to `tests/fixtures/`. Preserve shared editor settings and runtime whitelist per user feedback. Update CI/README to match new paths.

Inventory (root-level items)
- [`.dockerignore`](.dockerignore:1)
- [`.flake8`](.flake8:1)
- [`.gitignore`](.gitignore:1)
- [`Dockerfile`](Dockerfile:1)
- [`LICENSE`](LICENSE:1)
- [`main.py`](main.py:1)
- [`cli_tester.py`](cli_tester.py:1)
- [`pytest.ini`](pytest.ini:1)
- [`QUICK_REFERENCE.md`](QUICK_REFERENCE.md:1)
- [`QUICKSTART.md`](QUICKSTART.md:1)
- [`README.md`](README.md:1)
- [`renovate.json`](renovate.json:1)
- [`requirements-dev.txt`](requirements-dev.txt:1)
- [`requirements.txt`](requirements.txt:1)
- [`sample-response.json`](sample-response.json:1)
- [`security.py`](security.py:1)
- [`session_manager.py`](session_manager.py:1)
- [`setup.cfg`](setup.cfg:1)
- [`start_server.sh`](start_server.sh:1)
- [`TESTING.md`](TESTING.md:1)
- [`tools.py`](tools.py:1)
- [`transformer.py`](transformer.py:1)
- [`whitelist.txt`](whitelist.txt:1)
- [`.github/`](.github/:1)
- [`.vscode/`](.vscode/:1)
- [`docs/`](docs/:1)
- [`tests/`](tests/:1)

Categorization
- Source code: [`transformer.py`](transformer.py:1), [`tools.py`](tools.py:1), [`security.py`](security.py:1), [`session_manager.py`](session_manager.py:1)
- Scripts / entrypoints: [`main.py`](main.py:1), [`cli_tester.py`](cli_tester.py:1), [`start_server.sh`](start_server.sh:1)
- Tests: [`tests/`](tests/:1)
- Documentation: [`README.md`](README.md:1), [`docs/`](docs/:1), [`TESTING.md`](TESTING.md:1), [`QUICKSTART.md`](QUICKSTART.md:1)
- Config / tooling: [`.flake8`](.flake8:1), [`setup.cfg`](setup.cfg:1), [`pytest.ini`](pytest.ini:1), [`requirements*.txt`](requirements.txt:1)
- CI: [`.github/`](.github/:1) (preserve folder structure)
- IDE settings (shared): [`.vscode/`](.vscode/:1) (keep in repo per feedback)
- Fixtures / test data: [`sample-response.json`](sample-response.json:1)
- Runtime data (must remain): [`whitelist.txt`](whitelist.txt:1)

Proposed top-level layout (concrete)
- src/oig_cloud_mcp/ — Python package sources (package code goes here)
- bin/ — executable scripts and thin wrappers (python & shell entrypoints)
- tests/ — tests & fixtures (keep; add `tests/fixtures/`)
- docs/ — documentation (keep)
- config/ — runtime configuration (optionally host `whitelist.txt` if code uses `config/whitelist.txt`; current requirement: keep runtime file available)
- .github/ — CI workflows (preserve structure exactly)
- .vscode/ — shared editor settings (preserve in place)
- build/, dist/ — reserved for artifacts (gitignored)

Explicit moves and renames (source → destination)
- [`main.py`](main.py:1) → `bin/main.py`
- [`cli_tester.py`](cli_tester.py:1) → `bin/cli_tester.py`
- [`start_server.sh`](start_server.sh:1) → `bin/start_server.sh`
- [`transformer.py`](transformer.py:1) → `src/oig_cloud_mcp/transformer.py`
- [`tools.py`](tools.py:1) → `src/oig_cloud_mcp/tools.py`
- [`security.py`](security.py:1) → `src/oig_cloud_mcp/security.py`
- [`session_manager.py`](session_manager.py:1) → `src/oig_cloud_mcp/session_manager.py`
- [`sample-response.json`](sample-response.json:1) → `tests/fixtures/sample-response.json`
- [`QUICK_REFERENCE.md`](QUICK_REFERENCE.md:1) → `docs/quick_reference.md`
- [`QUICKSTART.md`](QUICKSTART.md:1) → `docs/quickstart.md`
- [`TESTING.md`](TESTING.md:1) → `docs/testing.md`
- Keep at root (no move): [`.flake8`](.flake8:1), [`requirements.txt`](requirements.txt:1), [`requirements-dev.txt`](requirements-dev.txt:1), [`Dockerfile`](Dockerfile:1), [`renovate.json`](renovate.json:1), [`setup.cfg`](setup.cfg:1), [`README.md`](README.md:1), [`LICENSE`](LICENSE:1), [`.dockerignore`](.dockerignore:1), [`.gitignore`](.gitignore:1)
- Preserve [`whitelist.txt`](whitelist.txt:1) at its current path unless you update runtime code to reference `config/whitelist.txt`. User requirement: whitelist must remain available to code execution.

Generated / build artifacts and .gitignore updates
- Append to [`.gitignore`](.gitignore:1):
  - /build/
  - /dist/
  - /*.egg-info/
  - /.venv/
  - /.pytest_cache/
  - __pycache__/
  - *.pyc
  - /tests/fixtures/*.json (optional — if you prefer fixtures tracked, do NOT ignore)

Migration plan — ordered steps, estimate, priority, risk, rollback
Step 0 — Prepare
- Create branch `chore/reorg-top-level`
- Run baseline checks: `pytest`, flake8
- Effort: 10–15m; Priority: High; Risk: Low; Rollback: delete branch

Step 1 — Create directories and move docs/fixtures (non-invasive)
- Create `bin/`, `src/oig_cloud_mcp/`, `tests/fixtures/`
- Move: [`sample-response.json`](sample-response.json:1) → `tests/fixtures/`; move QUICK* and TESTING to `docs/`
- Commit as single "move-only" commit
- Effort: 20–40m; Priority: High; Risk: Low; Rollback: revert commit

Step 2 — Move scripts and package code (moves only)
- Move `main.py`, `cli_tester.py`, `start_server.sh` → `bin/`
- Move package files into `src/oig_cloud_mcp/`
- Add minimal `__init__.py` to `src/oig_cloud_mcp/` (version metadata optional)
- Commit as "moves only"
- Effort: 30–60m; Priority: High; Risk: Medium (imports); Rollback: revert commit

Step 3 — Install editable & run tests (detect import breaks)
- Locally: `pip install -e .` or `PYTHONPATH=src pytest`
- Fix import paths in tests and code (separate commit)
- Effort: 30–90m; Priority: High; Risk: Medium; Rollback: revert commits

Step 4 — CI & Docker updates
- Update [`.github/workflows/ci.yml`](.github/workflows/ci.yml:1) to install package editable and run tests:
  - Example install snippet:
    - python -m pip install --upgrade pip && pip install -r requirements.txt -r requirements-dev.txt && pip install -e .
- Update `Dockerfile` to COPY/INSTALL from `src/` or install with pip
- Effort: 15–45m; Priority: High; Risk: Medium; Rollback: revert commits

Step 5 — Preserve shared settings & runtime files
- Leave [`.vscode/`](.vscode/:1) intact in repo (user-intended)
- Keep [`whitelist.txt`](whitelist.txt:1) available at runtime path; if you decide to move it to `config/`, change code paths in same commit
- Effort: 5–15m; Priority: High; Risk: Low; Rollback: trivial

Step 6 — Final verification and merge
- Run full local checks and push branch; fix CI failures; merge when green
- Effort: variable; Priority: High; Risk: Medium; Rollback: revert merge

Risk & rollback notes
- Primary risk: import path errors after move. Mitigation: use editable install (`pip install -e .`) and small atomic commits: (1) moves, (2) code edits, (3) CI/docs.
- Keep move-only commits to make rollback trivial.

README & CI precise updates
- README: update run example:
  - replace `python main.py` → `python bin/main.py` or instruct `python -m oig_cloud_mcp` after packaging
  - update sample fixture paths to `tests/fixtures/sample-response.json`
- CI (`.github/workflows/ci.yml`) suggested install & test steps:
```yaml
- name: Install
  run: python -m pip install --upgrade pip && pip install -r requirements.txt -r requirements-dev.txt && pip install -e .
- name: Run tests
  run: pytest -q
```
- Ensure lint steps point at `src/` or run against package import paths

Alternatives
- Minimal-preservation (low risk): only move [`sample-response.json`](sample-response.json:1) → `tests/fixtures/`, create `.gitignore` additions, leave flat layout. Effort: 15–30m.
- Aggressive refactor (higher effort): full packaging with `pyproject.toml`, `console_scripts` entrypoints, `Makefile`, publish workflow. Effort: 1–2 days; greater risk for import/packaging breakage.

Language / framework notes
- Python packaging best practice: use `src/` layout to avoid accidental imports from repo root.
- Keep tooling configs at repo root for CI/tool discoverability.
- Since [`whitelist.txt`](whitelist.txt:1) is required at runtime and `.vscode/` is intentionally shared, do not remove these files/folders as part of this refactor.

Next recommended immediate actions
1. Create branch `chore/reorg-top-level`.
2. Implement Step 1 (move docs/fixtures) as single commit.
3. Run tests and then implement Step 2 (move source & scripts), followed by Step 3 (fix imports).

End of plan.