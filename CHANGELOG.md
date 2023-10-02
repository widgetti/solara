# Changelog for Solara

## Changelog for v1.20.0

[Github Repository](https://github.com/widgetti/solara)

### Features
- **lab**: Added new component `ConfirmationDialog`. Commonly used to confirm actions such as deleting rows/objects from databases etc. ([#286](https://github.com/widgetti/solara/pull/286))

### Bug Fixes
- **tests**: Resolved issues with tests in Jupyter notebook being very flaky. ([#309](https://github.com/widgetti/solara/pull/309))
- **websocket**: Fixed corrupted websocket messages using Flask. The underlying library `wsproto` was identified as not thread safe. A mutex has been used to protect websocket calls. ([#308](https://github.com/widgetti/solara/pull/308))
- **theme**: The theme variant can now be set using environment variables. ([#304](https://github.com/widgetti/solara/pull/304))
- **jinja**: Settings are now passed correctly to the jinja template. Previously, command line arguments were not passed due to missing setter implementation. ([#303](https://github.com/widgetti/solara/pull/303))
- **subpackage**: All modules in the package now reload correctly when run as a subpackage. ([#293](https://github.com/widgetti/solara/pull/293))
- **ipyleaflet_advanced**: Fixed the web example for ipyleaflet_advanced. URL building issue for certain basemap variants was rectified. ([#269](https://github.com/widgetti/solara/pull/269))
- **memoize**: Fixed the `use_thread` on memoize which returned None after hit. ([#265](https://github.com/widgetti/solara/pull/265))
- **flask**: Converted flask websocket disconnect to a proper exception. (Commit ID: d287073)

### Refactors
- **reactive variables**: Moved `toestand` from `solara.lab` to `solara` as reactive variables are no longer experimental. ([#307](https://github.com/widgetti/solara/pull/307))

### CI Updates
- **dependencies**: Older versions of `traitlets` and `matplotlib` are now used to avoid type check failures. ([#305](https://github.com/widgetti/solara/pull/305))
- **anyio**: Fixed support for `anyio 4` typing. Adjusted for deprecated and renamed functions. ([#266](https://github.com/widgetti/solara/pull/266))

### Documentation
- **links**: Updated Vuetify links to v2 as Vuetify 3 is released. ([#236](https://github.com/widgetti/solara/pull/236))

### Merge Pull Requests
- Merged PR: Fixes for altair in Jupyter. ([#288](https://github.com/widgetti/solara/pull/288))
- Merged PR: Enhanced leaflet example with `on_bounds`. ([#270](https://github.com/widgetti/solara/pull/270))
