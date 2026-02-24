# Release Checklist

Follow these steps in order to make a release.

## Step 0: Switch to Master (or Main)

Make sure you are on the master (or main) branch with the latest changes before starting:

```bash
git checkout master
git pull upstream master
```

## Step 1: Determine Release Type

Check commits since last release to determine the release type:

```bash
git log $(git describe --tags --abbrev=0)..HEAD --oneline
```

- `patch` - Only `fix:` commits (bug fixes)
- `minor` - Any `feat:` commits (new features)

## Step 2: Check for JavaScript Package Changes (if any)

The release script will fail if there are unreleased JavaScript package changes. Check and release them first if needed:

```bash
# Check if JS packages have changes
(cd packages/solara-vuetify3-app && git diff $(git describe --tags --abbrev=0)..HEAD --stat .)

# If changes exist, release the JS package first
(cd packages/solara-vuetify3-app && ./release.sh <patch|minor|major>)
```

## Step 3: Run the Release Script

```bash
./release.sh <patch|minor>
```

The script will:
1. Check for unreleased JavaScript package changes (fails if any exist)
2. Bump version in all relevant files via bump2version
3. Create a commit and tag
4. Push to `upstream master`

## Step 4: Wait for PyPI Publish CI

Wait for the CI to publish packages to PyPI. The PyPI publish is part of the "Test" workflow (`.github/workflows/test.yaml`), which runs the `release` job after all tests pass when triggered by a version tag.

```bash
# List recent runs and find the Test run for the version tag (headBranch shows v1.x.x)
gh run list --limit=5

# Example output:
# queued  Bump version: 1.57.0 → 1.57.3  Test  v1.57.3  push  21209892447  ...
# queued  Bump version: 1.57.0 → 1.57.3  Test  master   push  21209892400  ...

# Watch the tag workflow (use the run ID from the v1.x.x row)
gh run watch 21209892447 --exit-status
```

The `release` job in the workflow only runs when:
1. All test jobs pass (build, code-quality, test-install, integration-test, unit-test)
2. The ref is a version tag (starts with `refs/tags/v`)

Packages published: `solara`, `solara-ui`, `solara-server`, `solara-assets`, `solara-enterprise`, `solara-meta`, `pytest-ipywidgets`

## Step 5: Update Changelog

After verifying the PyPI release, update the changelog with the new version:

1. Edit `solara/website/pages/changelog/changelog.md`
2. Add a new section for the version with the changes
3. Commit and push to master

```bash
git add solara/website/pages/changelog/changelog.md
git commit -m "docs: update changelog for version X.Y.Z"
git push upstream master
```

## Step 6: Push to Stable Branch

Push master to stable to trigger SSG rendering for the website:

```bash
git push upstream master:stable
```

## Step 7: Wait for Website Deploy CI

Wait for the webdeploy workflow to generate SSG pages:

```bash
gh run watch $(gh run list --workflow=webdeploy.yml --limit=1 --json databaseId -q '.[0].databaseId') --exit-status
```

This generates static pages and pushes them to `stable-ssg`.

## Step 8: Update Production Server

Update the server on nyx-cloud (see [SERVER.md](SERVER.md) for details).

**Important:** The production server runs on the `stable-ssg` branch, which is force-pushed by the webdeploy workflow. Use `git reset --hard` instead of `git pull`:

```bash
ssh nyx-cloud "cd /root/solara && git fetch origin && git reset --hard origin/stable-ssg && systemctl restart solara.service"
```

## Step 9: Verify Deployment

```bash
# Check the server is running
ssh nyx-cloud "systemctl status solara.service"

# Check deployed version
ssh nyx-cloud "cd /root/solara && git log -1 --oneline"
```

## Quick Reference

Complete release sequence (copy-paste friendly):

```bash
# 1. Run release
./release.sh <patch|minor>

# 2. Wait for PyPI publish (Test workflow on the version tag)
gh run list --limit=5  # Find the Test run ID for the v1.x.x tag (NOT master)
gh run watch <run-id> --exit-status  # Watch until complete

# 3. Update changelog
# Edit solara/website/pages/changelog/changelog.md, then:
git add solara/website/pages/changelog/changelog.md && git commit -m "docs: update changelog" && git push upstream master

# 4. Push to stable
git push upstream master:stable

# 5. Wait for website deploy
gh run watch $(gh run list --workflow=webdeploy.yml --limit=1 --json databaseId -q '.[0].databaseId') --exit-status

# 6. Update production server (stable-ssg is force-pushed, so use reset)
ssh nyx-cloud "cd /root/solara && git fetch origin && git reset --hard origin/stable-ssg && systemctl restart solara.service"
```

## Troubleshooting

### Release script fails due to JS package changes

Release the JavaScript package first, then retry:

```bash
(cd packages/solara-vuetify3-app && ./release.sh <patch|minor|major>)
./release.sh <patch|minor>
```

### PyPI publish CI fails

Check the CI logs for the error. Common issues:
- Version already exists on PyPI (need to bump version again)
- Authentication issues (check repository secrets)

### Need to fix the release commit

If you need to fix something in the release commit and keep history clean:

```bash
# Make your fix
git add -u

# Amend or rebase to fix the release commit
git rebase -i HEAD~3

# Force update the tag and push (replace vX.Y.Z with actual version)
git tag vX.Y.Z -f
git push upstream master vX.Y.Z -f
```

### Server fails to start after update

Check the logs and rollback if needed:

```bash
# Check logs
ssh nyx-cloud "journalctl -u solara.service -n 50"

# Rollback to previous version
ssh nyx-cloud "cd /root/solara && git checkout HEAD~1 && systemctl restart solara.service"
```

### Manual release (fallback)

If the release script doesn't work, release manually:

```bash
# Update solara/__init__.py with the new version
git add -u && git commit -m 'Release vX.Y.Z' && git tag vX.Y.Z && git push upstream master vX.Y.Z
```
