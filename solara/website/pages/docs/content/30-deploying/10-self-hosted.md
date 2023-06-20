# Self hosted deployment

 * [Flask](#flask)
 * [Starlette](#flask)
 * [FastAPI](#flask)
 * [Voila](#voila)
 * [Panel](#panel)
 * [Nginx](#nginx)


Solara runs on several web frameworks, such as

 * [Flask](https://flask.palletsprojects.com/)
 * [Starlette](https://www.starlette.io/) (and thus [FastAPI](https://fastapi.tiangolo.com/))

The simplest and most battle-tested way to deploy solara is via the `solara run` command. This uses Starlette under the hood:

    $ solara run app.py

If you do not use `solara run` to run your Solara app, configuration should go via environment variables instead of command-line argument. For instance, if you run the development server like `solara run myapp.py`, set the `SOLARA_APP` environment variable to `myapp.py`. For instance

    $ export SOLARA_APP=sol.py
    # run flask or starlette

or look at the examples below.

## Flask

For Flask, you can consult [the Flask documentation](https://flask.palletsprojects.com/deploying/).

A common solution is to use [gunicorn](https://gunicorn.org/) as the WSGI HTTP Server.

A typical command would be:
```
$ SOLARA_APP=sol.py gunicorn --workers 4 --threads=20 -b 0.0.0.0:8765 solara.server.flask:app
```

Note that we need at least 1 thread per user due to the use of a websocket.

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

Since FastAPI is built on Starlette, see the section on [Starlette](#starlette) about how to deploy a Starlette app.

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

Solara apps in Voila do not have support for [routing](/docs/understanding/routing)/[multipage](/docs/howto/multipage).


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

Solara apps in Panel do not have support for [routing](/docs/understanding/routing)/[multipage](/docs/howto/multipage).

## Nginx

If you use Nginx as a (reverse) proxy in front of your Python web server, a minimal
configuration would be:

```
server {
    server_name widgetti.io;
    listen 80
    location /solara/ {
            # the local solara server (could be using Starlette/uvicorn)
            proxy_pass http://localhost:8765/;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Script-Name /solara;  # informs solara to produce correct urls

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
    }
}
```

Note that if we use `location /` instead of `location /solara/`, we can skip the `proxy_set_header X-Script-Name /solara` line.

An alternative to using the `X-Script-Name` header with uvicorn, would be to pass the `--root-path` flag, e.g.:

```
$ SOLARA_APP=sol.py uvicorn --workers 1 --root-path /solara -b 0.0.0.0:8765 solara.server.flask:app
```
