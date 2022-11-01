# Deployment

 * [Deployment](#deployment)
    * [Flask](#flask)
    * [Starlette](#flask)
    * [FastAPI](#flask)
    * [Voila](#voila)
    * [Panel](#panel)
    * [Nginx](#nginx)


Solara runs on several web frameworks, such as
 * [Flask](https://flask.palletsprojects.com/)
 * [Starlette](https://www.starlette.io/) (and thus [FastAPI](https://fastapi.tiangolo.com/))

The development server uses Starlette, which means it is most battle-tested, but all solutions get tested in CI. Deploying using these frameworks thus is the same as deploying that framework.

The biggest difference with the development server is that all configurations should go via environment variables instead of command-line argument. For instance, if you run the development server like `solara run myapp.py`, we should instead set the `SOLARA_APP` environment variable to `myapp.py`. For instance

    $ export SOLARA_APP=myapp.py
    # run flask or starlette

or look at the examples below.

## Flask

For Flask, you can consult [the Flask documentation](https://flask.palletsprojects.com/deploying/).

A common solution is to use [gunicorn](https://gunicorn.org/) as the WSGI HTTP Server.

A typical command would be:
```
$ SOLARA_APP=myapp.py gunicorn --workers 1 -b 0.0.0.0:8765 solara.server.flask:app
```

Note that we explicitly set `--workers 1` such that it does not default to `$WEB_CONCURRENCY` which can be set to higher values, such as on Heroku. See the section on [Caveats](#caveats) why this matters.

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

    $ flask run
     * Running on http://127.0.0.1:5000/

## Starlette

For [Starlette](https://www.starlette.io/) we will assume [uvicorn](http://www.uvicorn.org/) for the ASGI webserver, and follow their [deployment documentation](https://www.uvicorn.org/deployment/), except we will not use gunicorn since we will not be using multiple workers yet.

```
$ SOLARA_APP=myapp.py uvicorn --workers 1 -b 0.0.0.0:8765 solara.server.flask:app
```

Note that we explicitly set `--workers 1` such that it does not default to `$WEB_CONCURRENCY` which can be set to higher values, such as on Heroku. See the section on [Caveats](#caveats) why this matters.


### Embedding in an existing Starlette application

If you already have a Starlette app and want to add your Solara app behind a prefix, say `'/solara/'`, you can mount the Solara routes to your existing app as follows.

```python
from starlette.applications import Starlette
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.responses import JSONResponse
import solara.server.starlette


def myroot():
    return JSONResponse({'framework': 'solara'})


routes = [
    Route("/", endpoint=myroot),
    Mount("/solara/", routes=solara.server.starlette.routes)
]

app = Starlette(routes)
```


## FastAPI

Since FastAPI is built on Starlette, see the section on [Starlette](#starlette) how to deploy a Starlette app.

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


## Voila

If you use want to use Voila, [you can use those deployment options](https://voila.readthedocs.io/en/stable/deploy.html).

Make sure you run a notebook where you display the app, e.g.
```python
@solara.component
def Page():
    ...
element = Page()
display(element)
```

Or consider using [Voila-vuetify](https://github.com/voila-dashboards/voila-vuetify)


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
$ SOLARA_APP=myapp.py uvicorn --workers 1 --root-path /solara -b 0.0.0.0:8765 solara.server.flask:app
```


## Caveats
Currently, using multiple workers requires sticky sessions on the `solara-context-id` cookie, so that the application context/state is in the same process the user connects to each time. Otherwise different connections may end up talking to different nodes or processes.

We plan to improve this situation in the future. In the meantime, please set your workers to 1, or go through the hassle of setting up multiple Python webservers and make your sessions sticky.
