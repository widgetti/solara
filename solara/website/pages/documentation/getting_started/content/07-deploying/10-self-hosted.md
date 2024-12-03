---
title: Deploying and hosting your own Solara app
description: Solara is compatible with many different hosting solutions, such as Flask, Starlette, FastAPI, and Voila.
---
# Self hosted deployment

 * [Flask](#flask)
 * [Starlette](#flask)
 * [FastAPI](#flask)
 * [Voila](#voila)
 * [Panel](#panel)
 * [Nginx](#nginx)
 * [Docker](#docker)


Solara runs on several web frameworks, such as

 * [Flask](https://flask.palletsprojects.com/)
 * [Starlette](https://www.starlette.io/) (and thus [FastAPI](https://fastapi.tiangolo.com/))

The most straightforward and well-tested method to deploy Solara is through the `solara run` command:

    $ solara run sol.py --production

which uses Starlette under the hood.

Your `sol.py` file could resemble the following:

```python
import solara

clicks = solara.reactive(0)


@solara.component
def Page():
    color = "green"
    if clicks.value >= 5:
        color = "red"

    def increment():
        clicks.value += 1
        print("clicks", clicks)  # noqa

    solara.Button(label=f"Clicked: {clicks}", on_click=increment, color=color)
```


If you're aiming to integrate Solara with other web frameworks such as [Flask](https://flask.palletsprojects.com/deploying/), [Starlette](https://www.starlette.io/), or [FastAPI](https://fastapi.tiangolo.com/), you normally do not execute `solara run sol.py`.
Instead, start your chosen web framework as directed by their documentation and configure Solara via environment variables. For instance, instead of running the development server like `solara run sol.py`, set the `SOLARA_APP` environment variable to `sol.py`:

    $ export SOLARA_APP=sol.py
    # run flask or starlette

or look at the examples below for more detailed instructions per web framework. Note that when solara is used this way it [by default runs in production mode](https://solara.dev/documentation/advanced/understanding/solara-server).

## Flask

For Flask, you can consult [the Flask documentation](https://flask.palletsprojects.com/deploying/).

A common solution is to use [gunicorn](https://gunicorn.org/) as the WSGI HTTP Server.

A typical command would be:
```
$ SOLARA_APP=sol.py gunicorn --workers 4 --threads=20 -b 0.0.0.0:8765 solara.server.flask:app
```

Note that we need at least 1 thread per user due to the use of a websocket. *Make sure you understand the implications of using multiple workers by reading [about handling multiple workers with solara server](https://solara.dev/documentation/advanced/understanding/solara-server#handling-multiple-workers)*

### Embedding in an existing Flask application

If you already have a Flask app and want to add your Solara app behind a prefix, say `'/solara/'`, you can add the [Blueprint](https://flask.palletsprojects.com/blueprints/) to your existing app as follows.

```python
from flask import Flask
import solara.server.flask

app = Flask(__name__)
app.register_blueprint(solara.server.flask.blueprint, url_prefix="/solara/")

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"
```

Save this file as `"app.py"` and run

    $  SOLARA_APP=sol.py flask run
     * Running on http://127.0.0.1:5000/

If you navigate to [http://127.0.0.1:5000/solara](http://127.0.0.1:5000/solara) you should see the Solara app.

## Starlette

For [Starlette](https://www.starlette.io/) we will assume [uvicorn](http://www.uvicorn.org/) for the ASGI webserver and follow their [deployment documentation](https://www.uvicorn.org/deployment/):

```
$ SOLARA_APP=sol.py uvicorn --workers 4 --host 0.0.0.0 --port 8765 solara.server.starlette:app
```

*Make sure you understand the implications of using multiple workers by reading [about handling multiple workers with solara server](https://solara.dev/documentation/advanced/understanding/solara-server#handling-multiple-workers)*

### Embedding in an existing Starlette application

If you already have a Starlette app and want to add your Solara app behind a prefix, say `'/solara/'`, you can mount the Starlette routes for Solara to your existing app as follows.

```python
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

import solara.server.starlette


def myroot(request: Request):
    return JSONResponse({"framework": "solara"})


routes = [
    Route("/", endpoint=myroot),
    Mount("/solara/", routes=solara.server.starlette.routes),
]

app = Starlette(routes=routes)
```

Save this file as `"solara_on_starlette.py"` and run

```
$  SOLARA_APP=sol.py uvicorn solara_on_starlette:app
...
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
...
```

If you navigate to [http://127.0.0.1:8000/solara](http://127.0.0.1:8000/solara) you should see the Solara app.

## FastAPI

Since [FastAPI](https://fastapi.tiangolo.com/) is built on Starlette, see the section on [Starlette](#starlette) about how to deploy a Starlette app.

### Embedding in an existing FastAPI application

Use `app.mount` to mount the Solara app into your existing FastAPI app.

```python
from fastapi import FastAPI
import solara.server.fastapi

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


app.mount("/solara/", app=solara.server.fastapi.app)
```

Save this file as `"solara_on_fastapi.py"` and run

```
$  SOLARA_APP=sol.py uvicorn solara_on_fastapi:app
...
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
...
```

If you navigate to [http://127.0.0.1:8000/solara](http://127.0.0.1:8000/solara) you should see the Solara app.


## Voila

If you use Voila, [you can use those deployment options](https://voila.readthedocs.io/en/stable/deploy.html).

Make sure you run a notebook where you display the app, e.g.
```python
@solara.component
def Page():
    ...
element = Page()
display(element)
```

Or consider using [Voila-vuetify](https://github.com/voila-dashboards/voila-vuetify).

Solara apps in Voila do not have support for [routing](/documentation/advanced/understanding/routing)/[multipage](/documentation/advanced/howto/multipage).


## Panel

[Panel](https://panel.holoviz.org/) supports [IPyWidgets](https://panel.holoviz.org/reference/panes/IPyWidget.html), which
means we can also embed the resulting widget from Reacton or Solara. See their [section on deployment](https://panel.holoviz.org/user_guide/Server_Deployment.html) and use the following code as an example of how to include a react component.
```python
import panel as pn
import solara


@solara.component
def ButtonClick(label="Hi"):
    clicks, set_clicks = solara.use_state(0)
    def increment():
        set_clicks(clicks + 1)
    return solara.Button(f"{label}: Clicked {clicks} times", on_click=increment)

# this creates just an element, Panel doesn't know what to do with that
element = ButtonClick("Solara+Panel")
# we explicitly ask Reacton to render it, and give us the widget
button_widget, render_context = reacton.render_fixed(element)
# mark this panel to be served by the panel server
pn.panel(button_widget).servable()
```

For development/testing purposes, run this script as:

    $ panel serve solara_in_panel.py

Solara apps in Panel do not have support for [routing](/documentation/advanced/understanding/routing)/[multipage](/documentation/advanced/howto/multipage).

## Nginx

If you use Nginx as a (reverse) proxy in front of your Python web server, a minimal
configuration would be:

```
server {
    server_name widgetti.io;
    listen 80
    location / {
            # the local solara server (could be using Starlette/uvicorn)
            proxy_pass http://localhost:8765/;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
    }

    # If you do not host solara on the root path, you can use the following
    # location /solara/ {
    #        ...
    #        proxy_set_header X-Script-Name /solara;  # informs solara to produce correct urls
    #        ...
    # }
}
```

An alternative to using the `X-Script-Name` header with uvicorn, would be to pass the `--root-path` flag, e.g.:

```
$ SOLARA_APP=sol.py uvicorn --workers 1 --root-path /solara -b 0.0.0.0:8765 solara.server.starlette:app
```

In the case of an [OAuth setup](https://solara.dev/documentation/advanced/enterprise/oauth) it is important to make sure that the `X-Forwarded-Proto` and `Host` headers are forwarded correctly.
If you are running uvicorn (the default if you use `solara run ...`) you will need to configure uvicorn to trust these headers using e.g.:

```bash
export UVICORN_PROXY_HEADERS=1  # only needed for uvicorn < 0.10, since it is the default after 0.10
export FORWARDED_ALLOW_IPS = "127.0.0.1"  # 127.0.0.1 is the default, replace this by the ip of the proxy server
```

Make sure you replace the IP with the correct IP of the reverse proxy server (instead of `127.0.0.1`). If you are sure that only the reverse proxy can reach the solara server, you can consider
setting `FORWARDED_ALLOW_IPS="*"`.

## HTTPS

Solara does not support running in HTTPS (secure) mode directly. You can use a reverse proxy like Nginx, Traefik or Caddy to handle HTTPS for you.

However, when running solara via uvicorn, it is possible to run uvicorn with HTTPS enabled. For more information, see the uvicorn documentation:
 https://www.uvicorn.org/deployment/#running-with-https


An example command would be:

```
$ SOLARA_APP=sol.py uvicorn --host 0.0.0.0 --port 8765 solara.server.starlette:app --ssl-keyfile=./key.pem --ssl-certfile=./cert.pem
```

## Docker

There is nothing special about running Solara in Docker. The only things you probably need to change is the interface the server binds to.
Solara by default binds to localhost, so that it is not accessible from the outside world. Apart from that localhost (or `::1` in case of IPv6)
might not be available, you probably want the outside world to see your Solara app. For that, you can use `--host=0.0.0.0` or `--host=::` option to bind to all interfaces.

Your Dockerfile could look like:

```Dockerfile
FROM ....

...
CMD ["solara", "run", "sol.py", "--host=0.0.0.0", "--production"]

```

For a complete example, you can take a look at:
  * [https://huggingface.co/spaces/solara-dev/template](https://huggingface.co/spaces/solara-dev/template)
  * [https://huggingface.co/spaces/giswqs/solara-template/tree/main](https://huggingface.co/spaces/giswqs/solara-template/tree/main)
  * [https://github.com/opengeos/solara-template](https://github.com/opengeos/solara-template)
