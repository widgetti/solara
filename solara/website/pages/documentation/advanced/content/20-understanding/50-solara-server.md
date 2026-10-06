---
title: Understanding the way Solara server works
description: Solara server enables running ipywidgets-based applications as standalone dashboards and apps, allowing multiple "Virtual kernels" to share
   the same process for better performance and scalability.
---
# Solara server

The solara server enables running ipywidgets based applications without a real Jupyter kernel, allowing multiple "Virtual kernels" to share the same process for better performance and scalability.

## Installation

To install the solara server, run:

```bash
$ pip install "solara-server[starlette]"
$ # pip install solara # to get all solara packages
```

See [our installation guide](/documentation/getting_started/installing) for more information.

## WebSocket in Solara
Solara uses a WebSocket to transmit state and updates directly from the server to the browser. This ensures that the state remains centralized on the server, facilitating state transitions server-side and enabling live updates to be pushed directly to the browser.


## Virtual Kernels
Normally when a browser page connects to a Solara server, a virtual kernel is created and is assigned a unique identifier termed a "Kernel ID." Should a WebSocket disconnection occur, Solara attempts to re-establish the connection, sending the Kernel ID during this process. If the server recognizes this ID (and the requested kernel hasn't expired) the Solara app resumes operations seamlessly.

### Virtual kernel lifecycle
Closing a browser page will directly shut the virtual kernel down (if this page was the last known page to the Solara server). This ensures that active closing of pages will directly clean up any memory usage on the server side for this kernel.

However, when the websocket between the web page and the server disconnects, the server keeps the kernel alive for 24 hours after the closure of the last WebSocket connection. The duration is customizable through the `SOLARA_KERNEL_CULL_TIMEOUT` environment variable. This feature is particularly handy in scenarios where devices like computers hibernate, leading to WebSocket disconnections. Upon awakening and subsequent WebSocket reconnection, the Solara app picks up right where it left off.

To optimize memory usage or address specific needs, one might opt for a shorter expiration duration. For instance, setting `SOLARA_KERNEL_CULL_TIMEOUT=1m` will cause sessions to expire after just 1 minute. Other possible options are `2d` (2 days), `3h` (3 hours), `30s` (30 seconds), etc. If no units are given, seconds are assumed.

### Maximum number of kernels connected

Each virtual kernel runs in its own thread, this ensures that one particular user (actually browser page) cannot block the execution of another virtual kernel. However, each thread consumes a bit of resources. If you want to limit the number of kernels, this can be done by setting the `SOLARA_KERNELS_MAX_COUNT` environment variable. The default is unlimited (empty string), but you can set it to any number you like. If the limit is reached, the server will refuse new connections until a kernel is closed.


## Handling Multiple Workers

In setups with multiple workers, it's possible for a page to (re)connect to a different worker than its original. This can happen after a lost network connection is restored, or when [ipypopout](https://github.com/widgetti/ipypopout) is used, since ipypopout creates a new connection, which can end up at a different worker. This can result in a loss of the virtual kernel, since it lives on the worker that was first connected to. The Solara app will then initiate a fresh start, or simply fail when ipypopout is used. To prevent this scenario, a sticky session configuration is recommended, ensuring consistent client-worker connections. A load balancer, such as [nginx](https://www.nginx.com/), can be used to achieve this. Note that using multiple workers (e.g. by using gunicorn) cannot work since a connection will be made to a different worker each time.

Sticky sessions remain the routing fast path, but they cannot help when the original worker is *gone* — a crash, an autoscaler scale-in, spot reclamation, or a rolling deploy whose sessions outlive the drain window. For those cases you can opt selected reactive variables into a shared backend (Redis), so a fresh worker restores them and the client re-mounts without the refresh dialog. See [State persistence and failover recovery](/documentation/advanced/understanding/state-persistence) for the application-side API and recovery model, and [Scaling out with state persistence](/documentation/getting_started/deploying/state-persistence) for the Redis and operations setup.

If you have questions about setting this up, or require assistance, please [contact us](https://solara.dev/docs/contact).

## Sessions

Solara uses a browser cookie (named `solara-session-id`) to store a unique session id. This session id is available via [get_session_id()](https://solara.dev/api/get_session_id) and is the same for all
browser pages. This can be used to store state that outlives a page refresh.

We recommend storing the state in an external database, especially in the case of multiple workers/nodes. If you want to store state associated to a session in-memory, make sure to set up sticky sessions.


The `solara-session-id` cookie is accessible in the browser using JavaScript. If you deem this a security risk, you can disable the cookie by setting the `SOLARA_SESSION_HTTP_ONLY` environment variable to `True`.


## Readiness check

To check if the server is ready to accept request, the `/readyz` endpoint is added, and should return a 200 HTTP status code, e.g.:

```
$ curl http://localhost:8765/readyz
curl -I localhost:8765

HTTP/1.1 200 OK
...
```

## Live resource information


To check resource usage of the server (CPU, memory, etc.), the `/resourcez` endpoint is added, and should return a 200 HTTP status code and include
various resource information, like threads created and running, number of virtual kernels, etc. in JSON format. To get also memory and cpu usage, you can include
the `?verbose` query parameter, e.g.:

```
$ curl http://localhost:8765/resourcez\?verbose
```

The JSON format may be subject to change.

## Ignoring notebook extensions

Not all (classic) jupyter notebook extensions are compatible with Solara, and there is not way to distinguish between notebook extensions that are needed for widgets and those that are not.
To ignore notebook extensions, you can set the `SOLARA_SERVER_IGNORE_NBEXTENSIONS` environment variable. This is a comma separated list of notebook extensions to ignore. For example, to ignore the `dash/main` and `foo/bar` extensions, you can run:

```bash
$ SOLARA_SERVER_IGNORE_NBEXTENSIONS="dash/main,foo/bar" solara run nogit/sol.py -a
```

Note that these error are not fatal, and the Solara app will still run.

## Production mode

By default, solara runs in development mode. This means, it will:

   * Automatically [reload your project files](/documentation/advanced/reference/reloading) by watching files on the filesystemn
   * Load debug version of the CSS files and JavaScript files for improved error messages (which leads to larger asset files).

To disabled all of these option, pass the `--production` flag, or set the environment variable `SOLARA_MODE=production`.

## Frontend features

The page that the Solara server sends to the browser loads the frontend code in parts, called features.
By default, the page preloads all features (the `full` preset), so every widget renders at once.
If your app does not use some features, you can leave them out, and the page loads faster.

Use the `--frontend` option, the `SOLARA_FRONTEND` environment variable, or `solara.server.settings.main.frontend`.
The value is a preset, `full` or `minimal`, followed by `+feature` or `-feature`:

```bash
# everything, except the mermaid diagrams
$ solara run sol.py --frontend=full,-mermaid
# only Vue and the widget core, plus math rendering
$ SOLARA_FRONTEND=minimal,+katex solara run sol.py
```

The features are:

| Feature | What it gives |
| - | - |
| `vuetify` | Vuetify and the Vuetify page shell. Needs `mdi`. Roboto and Vuetify's CSS come with `vuetify`; add `-roboto` to use your own font, and `-vuetify-css` to use your own Vuetify CSS. |
| `vuetify-css` | Vuetify's stylesheet. Comes with `vuetify`; add `-vuetify-css` to use your own Vuetify CSS. |
| `mdi` | The Material Design Icons font (`mdi-*` icons). |
| `material-icons` | The Material Icons font. |
| `roboto` | The Roboto font. Comes with `vuetify`; add `-roboto` to use your own font. |
| `font-awesome` | The Font Awesome icons (replaces `SOLARA_ASSETS_FONTAWESOME_ENABLED`, which still works). |
| `jupyter-controls` | The ipywidgets controls (`IntSlider`, `Button`, ...). Needs `jupyter-css`. |
| `output-widget` | The ipywidgets `Output` widget. Needs `jupyter-css`. |
| `jupyter-css` | The CSS of the ipywidgets controls. |
| `katex` | Math rendering (KaTeX), for example in `solara.Markdown`. |
| `mermaid` | Mermaid diagrams in `solara.Markdown`. The page never preloads it: when it is on, it loads when the first `solara.Markdown` mounts. |
| `vue-sfc` | The full Vue single-file-component compiler of ipyvue, for templates with `<script setup>`, `<style scoped>` or `lang="ts"`. Vue 3 only. |

The `minimal` preset has none of these features. Vue, the widget core and the notebook extensions are always on.

A feature that the page does not preload still works: the browser loads it the first time a widget needs it.
That first render is slower, so the server logs a warning (once per feature) that names the flag to add, for example `--frontend=minimal,+jupyter-controls`.
The browser console shows the same warning.
With `SOLARA_DEFAULT_CONTAINER=Fragment`, `minimal` loads `jupyter-controls` the first time a component renders more than one element without a container, because reacton then wraps those elements in its `Fragment`, an ipywidgets `VBox`.
The fonts and icon sets are an exception: the browser never loads `material-icons`, `roboto` or `font-awesome` on demand by themselves, and nothing warns.
Without them, text uses a fallback font and those icons do not show, so add them when your app uses them.
Vuetify's icons use `mdi`, so `mdi` always loads together with `vuetify`, also on demand.
Vuetify's text styles use the Roboto font, so Roboto comes with `vuetify`, also on demand.
Add `-roboto` to use your own font, for example `--frontend=minimal,+vuetify,-roboto`.
Vuetify's stylesheet (`vuetify-css`) also comes with `vuetify`, also on demand.
Use `-vuetify-css` when you ship your own Vuetify CSS (for example built from Vuetify's SASS) in `assets/`, for example `--frontend=full,-vuetify-css`.
Vuetify still adds the stylesheet of its theme colors from JavaScript; `-vuetify-css` does not remove that one.
On Vue 3, ipyvuetify 3.0.0 also adds its own copy of Vuetify's CSS to the page, which `-vuetify-css` does not remove; ipyvuetify 3.1.0 and newer do not add it.

Without `vuetify`, the page uses a shell without Vuetify, and the layout components (such as `solara.Column` and `solara.Row`) render without Vuetify.
This shell has no dark mode: Vuetify widgets that load on demand use the light colors of `solara.lab.theme`.
Solara then uses no default layout (`AppLayout`), so `solara.Sidebar`, `solara.AppBar` and `solara.AppBarTitle` show nothing, unless you use `solara.AppLayout` or a layout of your own; the server logs a warning when that happens.
On Vue 2 (ipyvue < 3), Vuetify is always on, and so is `mdi`; `roboto` and `vuetify-css` come with it, unless you add `-roboto` or `-vuetify-css`.
This setting only applies to the Solara server; Jupyter (notebook, lab, Voila) always loads everything.
A page that is open keeps the features it loaded with, also after a hot reload that changes the setting; refresh the page to use the new setting.

## Telemetry

Solara uses Mixpanel to collect usage of the solara server. We track when a server is started, stopped and a daily report of the number of unique users and connections made. To opt out of mixpanel telemetry, either:

 * Set the environmental variable `SOLARA_TELEMETRY_MIXPANEL_ENABLE` to `False`.
 * Install [python-dotenv](https://pypi.org/project/python-dotenv/) and put `SOLARA_TELEMETRY_MIXPANEL_ENABLE=False` in a `.env` file.
 * Run in auto restart mode (e.g. using `$ solara run sol.py --auto-restart`)
