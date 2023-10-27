# Solara server

The solara server enables running ipywidgets based applications without a real Jupyter kernel, allowing multiple "Virtual kernels" to share the same process for better performance and scalability.

## Readiness check

To check if the server is ready to accept request, the `/readyz` endpoint is added, and should return a 200 HTTP status code, e.g.:

```
$ curl http://localhost:8765/readyz
curl -I localhost:8765

HTTP/1.1 200 OK
...
```


## Production mode

By default, solara runs in development mode. This means, it will:

   * Automatically [reload your project files](docs/reference/reloading) by watching files on the filesystemn
   * Load debug version of the CSS files and JavaScript files for improved error messages (which leads to larger asset files).

To disabled all of these option, pass the `--production` flag, or set the environment variable `SOLARA_MODE=production`.

## Telemetry

Solara uses Mixpanel to collect usage of the solara server. We track when a server is started, stopped and a daily report of the number of unique users and connections made. To opt out of mixpanel telemetry, either:

 * Set the environmental variable `SOLARA_TELEMETRY_MIXPANEL_ENABLE` to `False`.
 * Install [python-dotenv](https://pypi.org/project/python-dotenv/) and put `SOLARA_TELEMETRY_MIXPANEL_ENABLE=False` in a `.env` file.
 * Run in auto restart mode (e.g. using `$ solara run sol.py --auto-restart`)
