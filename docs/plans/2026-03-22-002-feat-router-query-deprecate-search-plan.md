---
title: "feat: add Router.query, deprecate Router.search"
type: feat
status: active
date: 2026-03-22
upstream_issue: https://github.com/widgetti/solara/issues/524
repo: widgetti/solara
merge_confidence: 9
confidence_factors:
  implementability: 3
  scope: 2
  maintainer_activity: 2
  label_quality: 1
  recency: 0.5
  engagement: 0.5
---

# feat: add Router.query, deprecate Router.search

## Issue
Router.search returns the query string without the leading "?" which is inconsistent
with the URL spec (Location.search should include "?"). Rather than break existing
behavior, add Router.query (without "?") and deprecate Router.search with a warning.

## Implementation
- `solara/routing.py`: Rename internal `self.search` to `self.query`, add deprecated
  `.search` property with DeprecationWarning
- `solara/test/pytest_plugin.py`: Update internal usage from `.search` to `.query`
- `tests/unit/router_test.py`: Update tests to use `.query`, add coverage for None case

## Evidence
- Maintainer (@maartenbreddels) explicitly specified the API: "router.query == 'a=1&b=2'"
  and "turn .search into a property with deprecation warning"
- Issue comment: https://github.com/widgetti/solara/issues/524#issuecomment-2
