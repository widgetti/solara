# Solara server

The solara server enables running ipywidgets based applications without a real Jupyter kernel, allowing multiple "Virtual kernels" to share the same process for better performance and scalability.


## Telemetry

Solara uses Mixpanel to collect usage of the solara server. We track when a server is started and stopped. To opt out of mixpanel telemetry, either:

 * Set the environmental variable `SOLARA_TELEMETRY_MIXPANEL_ENABLE` to `False`.
 * Install [python-dotenv](https://pypi.org/project/python-dotenv/) and put `SOLARA_TELEMETRY_MIXPANEL_ENABLE=False` in a `.env` file.
