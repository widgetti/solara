
This is the old changelog, check the [Solara website](https://solara.dev/changelog) for the up to date changelog.

## Changelog for solara v1.22

### NEw Features
1. **WebSocket Reconnection**: Solara now supports a WebSocket that can reconnect, attempting to restore the page session, which enhances the user experience by removing the necessity for browser refreshes.
   - Addresses issues #254 and #161.

2. **Kernel Reconnection**: Added the ability to reconnect to an existing kernel and display a widget by its ID. This facilitates utilities like ipypopout to open a new browser window and display a widget that's operational in the main window.
   - This feature is limited to the same browser for security reasons, as the session_id must match.

3. **Kernel ID Usage**: The software has transitioned from using the jupyter `session_id` to `kernel_id` for identifying "AppContexts". The newly defined "AppContext" is now named "VirtualKernelContext".

### Fixes
1. **Loader Display**: Resolved an issue where the loader was placed inside a max-width container, causing it to not be centered.

2. **Test Fixture**: Addressed a problem in the `solara_test` fixture. If one test failed, it would cause all following tests to fail due to improper cleanup.

3. **Other Minor Fixes**:
   - Adjusted the centering method of the spinner for a better appearance with `ipypopout`.
   - Solara's documentation includes a new example demonstrating `use_router`.
   - Ploomber Cloud has been added to the documentation as a hosted option.
   - Improvements to test robustness and stability.

### Refactors
1. **Spinner Display**: The spinner display method was revamped for better compatibility with `ipypopout`.

### Documentation
Several documentation updates have been made, particularly around how to integrate Solara in different contexts and scenarios.

---

Overall, this version emphasizes better connection stability, especially for WebSockets and kernels. The improvements aim for a more seamless user experience and enhanced test robustness.


## Changelog for solara v1.21

[Github Repository](https://github.com/widgetti/solara)

### New Features
- **docs**: Added an example demonstrating menu, context menu, and dialog. (Commit: b617d4c)
- **docs**: Added a live update example which demonstrates pushing data from the python/server side. ([#229](https://github.com/widgetti/solara/pull/229))
- **feat**: Added a warning to the user when modules can potentially be loaded twice. This can lead to behaviors like reactive variables existing twice. ([#284](https://github.com/widgetti/solara/pull/284))
- **feat**: Implemented event support in `component_vue` for calling Python callbacks. Now, arguments like 'event_foo' will be available as the function foo in the Vue template. ([#312](https://github.com/widgetti/solara/pull/312))
- **feat**: Introduced new components `Menu`, `ClickMenu`, and `ContextMenu` for `solara.lab` which facilitate popup menus for buttons and context menus. ([#295](https://github.com/widgetti/solara/pull/295))
- **feat**: Support added for `on_relayout` in plotly, enabling image annotation. This update also brings an example demonstrating this feature. ([#285](https://github.com/widgetti/solara/pull/285))

### Refactors
- **refactor**: Optimized the `ipywidgets_runner` fixture to avoid running all runners every time it's invoked. This is aimed to improve the performance of the tests and possibly reduce their flakiness. ([#310](https://github.com/widgetti/solara/pull/310))

### Documentation Updates
- **docs**: Added a how-to guide for debuggers. ([#184](https://github.com/widgetti/solara/pull/184))
- **docs**: Provided clarity on integrating `solara` into existing web frameworks. (Commit: 14fd00f)

### Bug Fixes
- **fix**: The `baseUrl` is no longer suffixed with `/jupyter`. This was discovered to be unnecessary and a potential bug when working with `ipypopout`. ([#318](https://github.com/widgetti/solara/pull/318))
- **fix**: The search query is now passed directly to solara, preventing a UI flicker previously caused by updating the search query post initialization. ([#320](https://github.com/widgetti/solara/pull/320))
- **fix**: Resolved an issue with `starlette websocket` where the close function was calling itself recursively. It now correctly calls close on the websocket implementation. ([#317](https://github.com/widgetti/solara/pull/317))
- **fix**: Removed unnecessary special support for `pyodide`. (Commit: 4191fd0)


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
