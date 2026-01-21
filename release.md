# Release Checklist

Follow these steps in order to make a release.

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

Wait for the CI to publish packages to PyPI:

```bash
gh run watch $(gh run list --workflow=release.yml --limit=1 --json databaseId -q '.[0].databaseId')
```

Packages published: `solara`, `solara-server`, `solara-assets`, `solara-enterprise`, `solara-meta`, `pytest-ipywidgets`

## Step 5: Push to Stable Branch

Push master to stable to trigger SSG rendering for the website:

```bash
git push upstream master:stable
```

## Step 6: Wait for Website Deploy CI

Wait for the webdeploy workflow to generate SSG pages:

```bash
gh run watch $(gh run list --workflow=webdeploy.yml --limit=1 --json databaseId -q '.[0].databaseId')
```

This generates static pages and pushes them to `stable-ssg`.

## Step 7: Update Production Server

Pull the changes on nyx-cloud and restart the service (see [SERVER.md](SERVER.md) for details):

```bash
ssh nyx-cloud "cd /root/solara && git pull && systemctl restart solara.service"
```

## Step 8: Verify Deployment

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

# 2. Wait for PyPI publish
gh run watch $(gh run list --workflow=release.yml --limit=1 --json databaseId -q '.[0].databaseId')

# 3. Push to stable
git push upstream master:stable

# 4. Wait for website deploy
gh run watch $(gh run list --workflow=webdeploy.yml --limit=1 --json databaseId -q '.[0].databaseId')

# 5. Update production server
ssh nyx-cloud "cd /root/solara && git pull && systemctl restart solara.service"
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

# Force update the tag and push
git tag v1.57.0 -f
git push upstream master v1.57.0 -f
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
git add -u && git commit -m 'Release v1.57.0' && git tag v1.57.0 && git push upstream master v1.57.0
```
