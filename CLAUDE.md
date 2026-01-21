# CLAUDE.md

This file provides guidance for Claude Code (claude.ai/claude-code) when working with this repository.

## Project Overview

Solara is a pure Python, React-style framework for building Jupyter and web applications. It uses a React-like API with ipywidgets, enabling component-based code and simple state management. Apps work both inside Jupyter Notebook and as standalone web apps.

## Repository Structure

- `solara/` - Main source code
  - `components/` - UI components (Button, FileBrowser, etc.)
  - `server/` - Solara server implementation
  - `hooks/` - React-style hooks (use_state, use_effect, etc.)
  - `website/` - Documentation website
- `tests/` - Test suite
  - `unit/` - Unit tests
  - `integration/` - Integration tests
- `packages/` - Sub-packages (solara-server, solara-enterprise, etc.)

## Development Commands

### Setting Up the Development Environment

Use `uv` to create a virtual environment and install dependencies:

```bash
# Create venv with Python 3.11
uv venv .venv --python 3.11

# Install all dev dependencies
uv pip install -r requirements-dev.txt --python .venv/bin/python
```

### Running Tests

```bash
# Run all unit tests
uv run pytest tests/unit/

# Run a specific test file
uv run pytest tests/unit/file_browser_test.py -v

# Run a specific test
uv run pytest tests/unit/file_browser_test.py::test_file_browser_watch_detects_new_file -v

# Run integration tests
uv run pytest tests/integration/
```

### Running the Server

```bash
uv run solara run sol.py
```

## Commit Message Convention

This project uses conventional commits. Format: `type: description`

Types:
- `feat:` - New features
- `fix:` - Bug fixes
- `chore:` - Maintenance tasks
- `ci:` - CI/CD changes
- `docs:` - Documentation updates
- `test:` - Test additions/changes
- `refactor:` - Code refactoring

Examples from git history:
- `feat: allow data function in file download to be a coroutine`
- `fix: false positive for returns in async defs for hook use`
- `chore: drop Python 3.7 support`
- `test: skip flaky test on windows`

## Testing Patterns

### Unit Tests

Unit tests use `solara.render_fixed()` for testing components:

```python
import solara

@solara.component
def Test():
    return solara.FileBrowser(tmpdir, watch=True)

div, rc = solara.render_fixed(Test(), handle_error=False)
# Access widgets via div.children
file_list = div.children[1]
# Use rc.close() when done
rc.close()
```

### Async Tests

For testing async functionality (e.g., file watching), use pytest-asyncio:

```python
@pytest.mark.asyncio
async def test_async_feature(tmpdir: Path):
    # ... test code with await
    await asyncio.sleep(0.1)
```

### Mocking

Use `unittest.mock.patch.object` for mocking module-level attributes:

```python
with unittest.mock.patch.object(solara.components.file_browser, "watchfiles", None):
    # Test behavior when watchfiles is not installed
```

## Key Dependencies

- `watchfiles` - For file watching functionality (always available for developers)
- `ipywidgets` - Widget framework
- `ipyvuetify` - Vuetify components for ipywidgets
- `reacton` - React-like rendering for ipywidgets

## Pull Request Workflow

### Creating a Branch

Before creating a new branch, always fetch the latest changes and create from the updated master:

```bash
# Fetch latest changes from remote
git fetch origin  # or 'git fetch upstream' depending on your remote configuration

# Create branch from updated master
git checkout -b feat/my-feature origin/master
```

### Creating a PR

```bash
# Make changes and commit (ideally squash into 1 commit)
git add .
git commit -m "feat: description of feature"

# If you have multiple commits, squash them before pushing
git rebase -i origin/master  # then squash/fixup commits into one

# Push and create PR
git push -u origin feat/my-feature
gh pr create --title "feat: description" --body "## Summary\n..."
```

### Updating a Branch

If master has changed since you created your branch:

```bash
git fetch origin
git rebase origin/master
# Resolve any conflicts, then force push
git push --force-with-lease
```

### CI Checks

After pushing a PR, CI runs ~34 checks including:
- **Code quality** (~1 min): ruff, mypy, pre-commit
- **Unit tests** (~2-5 min): Multiple Python versions (3.8, 3.12) and OS (ubuntu, macos, windows)
- **Integration tests** (~10-17 min): Browser-based tests with Playwright
- **Build/install tests** (~1-2 min): Package installation verification

Total CI time: **~15-20 minutes**

### Monitoring PR Status

```bash
# Check overall PR status
gh pr status

# Check specific PR checks
gh pr checks <pr-number>

# View failed job logs
gh run view <run-id> --job <job-id> --log-failed

# Re-run a failed job (useful for flaky tests)
gh run rerun --job <job-id>
```

### Common Flaky Tests

The Windows integration tests occasionally fail with server startup issues:
- `RuntimeError: Server at http://localhost:XXXXX does not seem to be running`

These are infrastructure timing issues, not code problems. Re-run the failed job with:
```bash
gh run rerun --job <job-id>
```
