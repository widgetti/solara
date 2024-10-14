# Solara Changelog

## Version 1.40.0
   * Feature: In Jupyter Notebook and Lab, Solara (server) now renders the [ipypopout](https://github.com/widgetti/ipypopout) window instead of Voila [#805](render ipypopout content in jupyter notebook and lab)
   * Feature: Support styling input field of [ChatInput component](https://solara.dev/documentation/components/lab/chat). [#800](https://github.com/widgetti/solara/pull/800).
   * Feature: [InputTextArea component](https://solara.dev/documentation/components/input/input) for multi line text input. [#801](https://github.com/widgetti/solara/pull/801). Contributed by [Alonso Silva](https://github.com/alonsosilvaallende)
   * Bug Fix: Markdown links triggered a JavaScript error. [#765](https://github.com/widgetti/solara/pull/765)

## Version 1.39.0

   * Feature: Add option to start Solara server on a random unused port (using `--port=0`). [#762](https://github.com/widgetti/solara/pull/762)
   * Bug Fix: Extension checking for e.g. ipyleaflet now work correctly on Amazon SageMaker Studio Lab. [#757](https://github.com/widgetti/solara/pull/757)
   * Bug Fix: Various solara components should now work correctly in notebooks viewed on vscode, colab and voila. [#763](https://github.com/widgetti/solara/pull/763)

## Version 1.38.0

   * Feature: We detect and warn when there are possible reverse proxy or uvicorn misconfigurations. [#745](https://github.com/widgetti/solara/pull/745)
   * Bug Fix: Auth redirect did not respect SOLARA_BASE_URL. [#747](https://github.com/widgetti/solara/pull/747)
   * Bug Fix: Support for `websockets >= 13.0` and large cookies. [#751](https://github.com/widgetti/solara/pull/751)
   * Bug Fix: Windows support was broken from version 1.35.0 to 1.37.2. This went undetected due to a CI configuration error. [#712](https://github.com/widgetti/solara/pull/712) [#739](https://github.com/widgetti/solara/pull/739)

## Version 1.37.2

   * Bug Fix: If matplotlib was imported before solara, we did not set the backend, now we do. [#741](https://github.com/widgetti/solara/pull/741)

## Version 1.37.1

   * Bug Fix: The newly introduced hooks validator could emit a warning on certain call syntax. This can fail CI pipelines that do now allow warnings [c7c3b6a](https://github.com/widgetti/solara/commit/c7c3b6ab2929c4da1ffc3ab8e2e423cf0cfa7567).

## Version 1.37.0

   * Feature: We now check if a component follows the rules of hooks https://solara.dev/documentation/advanced/understanding/rules-of-hooks [#706](https://github.com/widgetti/solara/pull/706)

      Use SOLARA_CHECK_HOOKS=off to disable this check in case this gives unexpected issues, [and please open an issue](https://github.com/widgetti/solara/issues/new).
   * Fix: solara-server skips directories when reading extensions which might cause a startup failure otherwise [#715](https://github.com/widgetti/solara/pull/715)

## Version 1.36.0
   * Feature: Provide a jupyter-widgets-popout-container css class on body for doing specific styling in combination with ipypoout [85c1899](https://github.com/widgetti/solara/commit/85c189919a42b2590558d9713fc3a2440f46b7c0)

## Version 1.35.1

   * Bug Fix: Vulnerability which allowed for accessing any file on the system. [CVE-2024-39903](https://nvd.nist.gov/vuln/detail/CVE-2024-39903)
     [391e212](https://github.com/widgetti/solara/commit/391e2124a502622fe7a04321a540af6f252d8d4b).
   * Bug Fix: On windows we now read all text files (like CSS) with utf8 encoding by default [681f69b](https://github.com/widgetti/solara/commit/681f69b7779da2bd3586d6e9fd0b21d36e6fb124)


## Version 1.35.0

   * Feature: On slower systems, pytest-ipywidgets could time out when connecting to the app, `PYTEST_IPYWIDGETS_SOLARA_APP_WAIT_TIMEOUT` can be set to increase the timeout. [c302caf](https://github.com/widgetti/solara/commit/c302caf520b6bd4825f4104ac4d629b1d9543607) and [Our testing docs](https://solara.dev/documentation/advanced/howto/testing).
   * Bug Fix: The sidebar container did not have `height: 100%` set, causing the sidebar to not fill the entire height of the page. [5358f0f](https://github.com/widgetti/solara/commit/5358f0f1b8582422041bfc6553e6d95e103a9aa9)
   * Bug Fix: Vulnerability which allowed for accessing any file on the system. [CVE-2024-39903](https://nvd.nist.gov/vuln/detail/CVE-2024-39903)
     [391e212](https://github.com/widgetti/solara/commit/391e2124a502622fe7a04321a540af6f252d8d4b). A follow up fix was need for this in 1.35.1, we recommend upgrading to that version.
   * Bug Fix: Allow the FileBrowser to navigate to the root on Windows [707](https://github.com/widgetti/solara/pull/707) - Contributed by Jochem Smit.

## Version 1.34.1

   * Bug Fix: Using `SOLARA_ASSETS_PROXY=False` (default on [py.cafe](https://py.cafe)) would break grid layout. [#705](https://github.com/widgetti/solara/pull/705)
   * Bug Fix: Hot reload work in more situations on Linux. [#702](https://github.com/widgetti/solara/pull/702)


## Version 1.34.0

   * Feature: Enhancements for Solara `InputDate` and `InputDateRange` components [#672](https://github.com/widgetti/solara/pull/672):
      * Limiting allowed dates with `min_date` and `max_date` arguments.
      * Monthly granularity with `date_picker_type="month"`.
      * `InputDateRange` selection can be sorted in ascending order with `sort` argument.
   * Bug Fix: Typo in `solara.Tooltip`. [#695](https://github.com/widgetti/solara/pull/695)
   * Bug Fix: `ipywidgets.Accordion` content was not hidden when closed. [#694](https://github.com/widgetti/solara/pull/694)
   * Bug Fix: `solara.Tooltip` would break any functionality in it's children that relied on the `blur`, `keydown`, or `focus` events. [#696](https://github.com/widgetti/solara/pull/696)
   * Bug Fix: Raise an error instead of showing a custom page on 404. Enables custom 404 pages in Solara apps. [#670](https://github.com/widgetti/solara/pull/670)
   * Bug Fix: Prevent broken installation by restricting Numpy version. [#687](https://github.com/widgetti/solara/pull/687) and [`286e196`](https://github.com/widgetti/solara/commit/286e196ee990af814768d0612b98b5138f5ceb51).

## Version 1.33.0

### Details

   * Feature: Add support for `color` argument to `solara.Switch`. [#658](https://github.com/widgetti/solara/pull/658)
   * Bug Fix: Support `define` for ES Modules when running with virtual kernel. [#668](https://github.com/widgetti/solara/pull/668)
   * Bug Fix: Typo in `NameError` message. [#666](https://github.com/widgetti/solara/pull/666)
   * Bug Fix: Show `solara.AppBar` when navigation tabs are the only child. [#656](https://github.com/widgetti/solara/pull/656)
   * Bug Fix: PermissionError for nbextensions on startup in `solara>=1.29`. [#648](https://github.com/widgetti/solara/pull/648)

## Version 1.32.2

### Details

   * Bug Fix: Theme change not behaving correctly for `solara.Markdown` and `ipywidgets`. [#636](https://github.com/widgetti/solara/pull/636)


## Version 1.32.1

### Details

   * Bug Fix: `solara.display` not working when running a solara server in production mode, or when running a Solara app with flask. [#622](https://github.com/widgetti/solara/pull/622)
   * Bug Fix: `solara.Markdown` would raise a `NameError` if `pymdown-extensions` was not installed. [#621](https://github.com/widgetti/solara/pull/621)


## Version 1.32.0

### Details

   * Feature: Support for multiple custom asset locations. [#602](https://github.com/widgetti/solara/pull/602)
   * Refactor: Improve API for working with third-party dataframes. [#600](https://github.com/widgetti/solara/pull/600)
   * Bug Fix: Give task results more unique keys. [#609](https://github.com/widgetti/solara/pull/609)
   * Bug Fix: Avoid closing kernel multiple times. [e5ca67b](https://github.com/widgetti/solara/commit/e5ca67b6be46a8d236cc127cc06068702aa40754)
   * Bug Fix: Make `page_close` beacon thread safe. [2501c83](https://github.com/widgetti/solara/commit/2501c83f135bc342ed9845198f7aff3bdcf09bc0)
   * Bug Fix: Viewing embedded Solara application in fullscreen could cause a Reacton error. [#603](https://github.com/widgetti/solara/pull/603)
   * Bug Fix: Remove fade when navigation is done from a thread/task. [#594](https://github.com/widgetti/solara/pull/594)
   * Bug Fix: Support Pydantic 1 and 2 in reactive variables. [#601](https://github.com/widgetti/solara/pull/601)

## Version 1.31

We changed solara from a single package into multiple packages.

The `solara` package is a meta package that installs all the necessary dependencies to get started with Solara. By default, we install:

  * [`pip install "solara-ui[all]"`](https://pypi.org/project/solara-ui)
  * [`pip install "solara-server[starlette,dev]"`](https://pypi.org/project/solara-ui)

Notebook users can simply install `solara-ui` if they do not need the solara-server. Read our [installation guide](https://solara.dev/documentation/getting_started/installing) for more information.

## Version 1.30.1

### Details

   * Bug Fix: Serialization error from attempt to serialize default event handles in `component_vue`. [793cbb1](https://github.com/widgetti/solara/commit/793cbb19d8c361490b7e0b1e436a3e9ef3acea71)
   * Bug Fix: `on_kernel_start` callback cleanups could have been triggered multiple times. [4b75ca9](https://github.com/widgetti/solara/commit/4b75ca934f4e905a3592911bfca6657e491d1425)
   * Bug Fix: Autorender did not render child routes. [#575](https://github.com/widgetti/solara/pull/575)


## Version 1.30.0

### Details

   * Feature: Multiple file support for `FileDrop`. [#562](https://github.com/widgetti/solara/pull/562)
   * Feature: Solara server is now compatible with Pyodide (threads are combined if they cannot be used). [#569](https://github.com/widgetti/solara/pull/569)
   * Bug Fix: Nested Vuetify apps were not displayed correctly. [#570](https://github.com/widgetti/solara/pull/570)
   * Bug Fix: `on_kernel_start` callbacks were accumulating on hot reload. [#556](https://github.com/widgetti/solara/pull/556)
   * Bug Fix: ES Modules were being loaded multiple times on hot reload. [#559](https://github.com/widgetti/solara/pull/559)
   * Bug Fix: Theme CSS was not loaded when `rootPath` was non-trivial. [829946c](https://github.com/widgetti/solara/commit/829946c4bf47a2ea78d783bb500faaab93b2549b)
   * Fix: `Route.component` is now rendered, instead of the internal `RenderPage` component. [#555](https://github.com/widgetti/solara/pull/555)
   * Fix: `Route.layout` now allows for layouts to be used when defining routes manually. [#554](https://github.com/widgetti/solara/pull/554)
   * Fix: Allow custom command like arguments that can be parsed by the application. [#558](https://github.com/widgetti/solara/pull/558)


## Version 1.29.1

### Details

   * Bug Fix: Solara installation failing when using [pixi](https://pixi.sh/latest/). [#553](https://github.com/widgetti/solara/pull/553)

## Version 1.29.0

<video width="80%" controls>
   <source src="https://solara-assets.s3.us-east-2.amazonaws.com/videos/solara-1.29-drawdata-na.mp4" type="video/mp4" >
</video>


### Highlights

  * Feature: Improved matplotlib support (pylab interface, display support) making it work more similar as in Jupyter. [#540](https://github.com/widgetti/solara/pull/540)
  * Feature: [use_dark_effective](https://solara.dev/api/use_dark_effective) to get the effective dark mode of the app, making it easier to support dark mode on the Python side [#551](https://github.com/widgetti/solara/pull/551).


### Details

   * Feature: [`/resourcez` endpoint](https://solara.dev/docs/understanding/solara-server) to get server resource statistics [#547](https://github.com/widgetti/solara/pull/547).
   * Bug fix: router.push to external links should not use history, allowing navigation to external links [11c6094](https://github.com/widgetti/solara/commit/11c6094f3c47528d40f8be951c1d322e454f98ea).
   * Bug fix: After upgrading widgets, solara server would still use the previous version due to browser cache [#523](https://github.com/widgetti/solara/pull/523).
   * Bug fix: [The example todo app](https://solara.dev/examples/utilities/todo) would not work because Ref(..) did not work in combination with use_reactive [#544](https://github.com/widgetti/solara/pull/544).

## Version 1.28.0

<video width="80%" controls>
   <source src="https://dxhl76zpt6fap.cloudfront.net/videos/solara-theme.mp4"  type="video/mp4" >
</video>

### Highlight

   * Feature: [Theming support](https://solara.dev/api/theming), including dark theme and auto-detection of device preference [#494](https://github.com/widgetti/solara/pull/494).

### Details

   * Feature: Support for [ES modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules) using [ipyReact](https://github.com/widgetti/ipyreact)
      [#516](https://github.com/widgetti/solara/pull/516).
   * Feature: Support for [Polars](https://pola.rs/) dataframes in `solara.DataFrame` [#195](https://github.com/widgetti/solara/pull/195)
   * Bug Fix: User reactive variables sometimes taking on the value of a solara builtin one (issue [#510](https://github.com/widgetti/solara/issues/510))
      [#514](https://github.com/widgetti/solara/pull/514)
   * Bug Fix: An extra scrollbar sometimes appearing when no `AppBar` or `SideBar` was present on the page [#477](https://github.com/widgetti/solara/pull/477)
   * Bug Fix: The browser main scrollbar being present on pages with no scrolling enabled [#518](https://github.com/widgetti/solara/pull/518)

## Version 1.27.0


<video width="80%" controls>
   <source src=https://dxhl76zpt6fap.cloudfront.net/videos/solara-tasks.mp4  type="video/mp4" >
</video>

### Highlight

   * Feature: [Task support](https://solara.dev/api/task). Lets you run code in the background, with the UI available to the user. This is useful for long running tasks, like downloading data or processing data [#461](https://github.com/widgetti/solara/pull/461).
   * Feature: Provide access to [cookies and request headers](https://solara.dev/api/cookies_headers) [#501](https://github.com/widgetti/solara/pull/501)
   * Refactor: Replace MathJax with KaTeX for faster math rendering and a lighter package [#483](https://github.com/widgetti/solara/pull/483)

## Version 1.26.0

### Demo of @solara.lab.computed with

<video width="80%" controls>
   <source src="https://github.com/widgetti/solara/assets/5592797/daf21bb0-ce94-4d5e-9ebb-339ea768b3ac" type="video/mp4" >
</video>

### Highlight

   * Feature: [computed reactive variables](https://solara.dev/api/computed) which use the return value of the function. The value will be updated when any of the reactive variables used in the function [#455](https://github.com/widgetti/solara/pull/455).

### Details

   * Feature: on_kernel_start triggers callback on virtual kernel start [#471](https://github.com/widgetti/solara/pull/471).
   * Bug fix: Altair works in VSCode and Google Colab [#488](https://github.com/widgetti/solara/pull/488).
   * Feature: get_kernel_id and get_session_id for custom storage [#452](https://github.com/widgetti/solara/pull/452).
   * Bug fix: Mermaid and Math rendering in Jupyter Lab and VSCode [#480](https://github.com/widgetti/solara/pull/480).

## Version 1.25.1

### Details

* Performance: Removed unnecessary CSS and JS.
* Performance: Quality of Life - JS and CSS resources automatically reloaded on version change.
* Bug fix: overlay disabling navigation for display width < 960px.


## Version 1.25.0


### Demo of a Chat GPT interface with medical 3d visualization

<video width="80%" controls>
   <source src="https://github.com/widgetti/solara/assets/1765949/ca149ab5-0bd3-4eea-9736-08e1e0b06771" type="video/mp4" >
</video>




### Highlight

 * Feature: Chat interface components for chatbots, chatrooms or conversational elements in your dashboards or apps [#384](https://github.com/widgetti/solara/pull/384)

### Details

 * Performance: Under starlette, we throttle sending websocket messages to get better performance, this is experimental and can be enabled by setting the
   environment variable `SOLARA_EXPERIMENTAL_PERFORMANCE=1` [#400](https://github.com/widgetti/solara/pull/400)
 * Performance: Reuse the jinja environment when rendering templates (this also saves memory).

## Version 1.24.0

### Demo of CSS hot reloading

<video width="80%" controls>
   <source src="https://github.com/widgetti/solara/assets/1765949/3a15b8fa-f38e-4376-ad05-330593d98de8" type="video/mp4" >
</video>


### Highlight

 * Feature: Hot reloading of css file used with Style components [#396](https://github.com/widgetti/solara/pull/396)
 * Bug fix: display() did not work in threads [#398](https://github.com/widgetti/solara/pull/398)
 * Bug fix: Support home directory on Windows.


### Details

 * Bug fix: Do not trigger re-render due to unneeded state in context [#386](https://github.com/widgetti/solara/pull/386)
 * Feature: Show number of widgets created and close when using --timing [#387](https://github.com/widgetti/solara/pull/387)


## Version 1.23.0

### Demo app 'TimeTrekker'

<video width="80%" controls>
   <source src="https://github.com/widgetti/solara/assets/1765949/17598728-0678-495b-955a-965ce9283200" type="video/mp4" >
</video>

### Demo app 'Wanderlust'

<video width="80%" controls>
   <source src="https://github.com/widgetti/wanderlust/assets/1765949/fe3db611-4f46-4ca3-b4c2-ace6d2b1493b" type="video/mp4" >
</video>


### Highlights

 * Feature: Solara now has a production mode (enabled by passing in `--production`) which will load optimized CSS and JS and disable hot reloading.
    Our [Solara server](https://solara.dev/documentation/advanced/understanding/solara-server) page contains more information about it. If you used `--reload` or
    `--dev` before you can now use the `-a/--auto-restart` flat. The `--dev` and `--reload` flags are kept for backwards compatibility.
 * Feature: All `Input` components expose the `style` and `classes` arguments for custom styling.
 * Feature: New component: [`InputDate` and `InputDateRange`](https://solara.dev/api/input_date) which use a datepicker in a menu. (#326)
 * Feature: The AppLayout component exposes the `style` and `classes` argument for custom styling: [#367](https://github.com/widgetti/solara/pull/367)
 * Feature: Initial support for ipyvue and ipyvuetify v3: [#364](https://github.com/widgetti/solara/pull/364)
 * Feature: The `InputText` now takes an `update_events` on argument for custom key combination. This also allows to opt-out of the 'blur' event triggering an on_value: [#376](https://github.com/widgetti/solara/pull/376)
 * Bug fix: When using a Sidebar or AppBar we would previously render the main `Page` component twice, this does not happen anymore: [#366](https://github.com/widgetti/solara/pull/366)
 * Documentation: Added a "Jupyter dashboard tutorial" part 1.
 * Documentation: Added documentation for [`use_effect`](https://solara.dev/api/use_effect), [`use_memo`](https://solara.dev/api/use_effect), and improved the documentation of [`use_thread`](https://solara.dev/api/use_thread).
 * Example: Added an [AI tokenizer app example](https://solara.dev/examples/ai/tokenizer)
 * Showcase: Added a reproduction of the [OpenAI Wanderlust app](https://solara.dev/showcase) to our showcases.


### Details

 * Feature: Menu supports use_activator_width argument, which can be set to false to not have the menu popup be the same with as the activator which is useful for fixed width components such as a date picker.
 * Feature:
 * Bug fix: Menu component avoids an extra div around the activator to not interfere with the layout: [#345](https://github.com/widgetti/solara/pull/345)
 * Bug fix: Menu could be closed or opened on a re-render.
 * Bug fix: Solara server failed to start in Docker when $HOME is not set or not writable.
 * Bug fix: Solara server should only try to watch files that exists for hot reloading: [#356](https://github.com/widgetti/solara/pull/356)
 * Bug fix: A ToggleButtons component using Buttons with `value=None` would cast it to a string (i.e. `value="None"`) : [#369](https://github.com/widgetti/solara/pull/369)
 * Bug fix: PyTest based tests using vue_component_registry would fail outside of solara context, tests should run normally now.
 * Bug fix: Our monkeypatched Output widget would raise an exception when `get_ipython` returns None such as in pytest based testing.
 * Bug fix: A custom `Layout` component was ignored when running solara as a module: [#368](https://github.com/widgetti/solara/pull/368)
 * Bug fix: A custom title was ignored when running solara as a script.
 * Bug fix: When a child component would overrwrite a meta tags, it now overwrites it.
 * Bug fix: do not use excessive memory when rendering markdown: [#382](https://github.com/widgetti/solara/pull/382)
