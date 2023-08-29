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

## WebSocket in Solara
Solara employs a WebSocket to transmit state and updates directly from the server to the browser. This ensures that all state remains centralized on the server, facilitating state transitions server-side and enabling live updates to be pushed directly to the browser.

### Page Session ID
Each browser page within Solara is assigned a unique identifier termed the "Page Session ID." Should a WebSocket disconnection occur, Solara attempts to re-establish the connection, sending the Page Session ID during this process. If the server recognizes this ID—indicating the session is still active and hasn't expired—the Solara app resumes operations seamlessly. Each Page Session ID is related to a single "Virtual kernel".

### Page Session Expiration
By default, the server retains a page session for 24 hours post the closure of the last WebSocket connection. However, this duration is customizable through the `SOLARA_PAGE_SESSION_RECONNECT_WINDOW` environment variable. This feature is particularly handy in scenarios where devices like computers hibernate, leading to WebSocket disconnections. Upon awakening and subsequent WebSocket reconnection, the Solara app picks up right where it left off.

To optimize memory usage or address specific needs, one might opt for a shorter expiration duration. For instance, setting `SOLARA_PAGE_SESSION_RECONNECT_WINDOW=1m` will cause sessions to expire after just 1 minute. Other possible options are
`2d` (2 days), `3h` (3 hours), `30s` (30 seconds), etc. If no units are given, seconds are assumed.

### Handling Multiple Workers
In setups with multiple workers, it's possible for a page to reconnect to a different worker than its original. This would result in a loss of the page session, prompting the Solara app to initiate a fresh start. To prevent this scenario, a sticky session configuration is recommended, ensuring consistent client-worker connections. Utilizing a load balancer, such as [nginx](https://www.nginx.com/), can achieve this.

Should you require assistance or have questions regarding this setup, please [contact us](https://solara.dev/docs/contact).


### Disconnect while running

If a client disconnects during an active process, Solara will buffer the outgoing messages. Upon reconnection, these buffered messages are then sent to the client. Messages are stored in a queue, which has a default limit of 1MB. If this queue reaches its capacity, the associated page session, and consequently, the virtual kernel, are terminated. To adjust the size of this queue, you can configure the `SOLARA_PAGE_SESSION_QUEUE_SIZE` environment variable. For example, setting `SOLARA_PAGE_SESSION_QUEUE_SIZE=1GB` allows for a larger buffer, reducing the likelihood of session termination but potentially increasing memory consumption.


## Telemetry

Solara uses Mixpanel to collect usage of the solara server. We track when a server is started, stopped and a daily report of the number of unique users and connections made. To opt out of mixpanel telemetry, either:

 * Set the environmental variable `SOLARA_TELEMETRY_MIXPANEL_ENABLE` to `False`.
 * Run in development mode (e.g. using `$ solara run sol.py --dev`)
 * Install [python-dotenv](https://pypi.org/project/python-dotenv/) and put `SOLARA_TELEMETRY_MIXPANEL_ENABLE=False` in a `.env` file.
