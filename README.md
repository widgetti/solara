# Making IPywidgets based web applications simple and fun

![logo](https://user-images.githubusercontent.com/1765949/159178788-2c20214d-d4fe-42cd-a28e-7097ce37c904.svg)

 * [What it is?](#what-it-is?)
 * [Example](#example)
 * [Usage](#usage)
 * [Deployment](#deployment)
    * [Flask](#flask)
    * [Starlette](#flask)
    * [FastAPI](#flask)
    * [Voila](#voila)
    * [Panel](#panel)
    * [Nginx](#nginx)
 * [Installation](#installation)
 * [Development](#development)
 * [FAQ](#faq)

# Live demo
[Live demo running Heroku](https://solara-demo.herokuapp.com/)

# What it is?

If you only care about using Solara from the Jupyter notebook (classic or lab) or Voila, it is:

   * A set of composable components build on [React-IPywidgets](https://github.com/widgetti/react-ipywidgets) (e.g., Image, Markdown, FileBrowser, etcetera) to get that 'all batteries included' feeling.
   * A powerful set of React hooks for cross-filtering, fetching data, downloading data, run long-running jobs in threads etc.


If you also want to develop and deploy a more extensive application and prefer not to program in a Jupyter notebook, or care about scaling your application, Solara is also:

   * An application server with a good Developer eXperience (DX):
       * Auto reloading refreshes the page when you save your script or Jupyter notebook.
       * Your app state is restored after reload/restart: All tabs, checkboxes, etcetera will be as you set them.
   * An application server that:
      * Runs on
        * Starlette (and thus FastAPI)
        *  Flask.
      * Executes:
         * Python scripts
         * Python modules/packages
         * Jupyter notebooks
   * An alternative for Voila, for when:
     * You only need to display widgets
     * One kernel/process per request is becoming a bottleneck/cost issue.
     * Only care about using Python (e.g., not Julia, R)
     * Are ok, or even prefer, to have your application code run in the same process as your web server (e.g., Starlette/FastAPI, Flask)


If you are already using [Panel](https://panel.holoviz.org/), you can [embed Solara components in their dashboard server](#panel).

To make it easier to use Solara, without directly having to use React-IPyWidgets, or Solara components, [we can also render regular IPyWidgets](#usage)


## How does Solara fit into the big picture?

By now, you maybe understand that Solara is actually two things. A server part that takes care of getting the widgets into the browser and a UI part, consisting of react components and hooks.

The UI parts is build on top of [React-IPywidgets](https://github.com/widgetti/react-ipywidgets) which is using the existing IPyWidgets stack.

If you use Jupyter, then you probably use the Jupyter notebook, Lab, of Voila to get your widgets into the browser.

If you don't use Jupyter, or don't know what it is, or are a ML Ops, Dev Ops, or Sys Admin, you are probably more interested in the Solara server.

![Solara stack](https://user-images.githubusercontent.com/1765949/168669118-da9410bf-e838-481c-925d-4754efa01b7b.png)

# Example

Lets start with a small example app by creating a file `myapp.py`:

```python
import react_ipywidgets as react
import react_ipywidgets.ipywidgets as w

@react.component
def ButtonClick(label="Hi"):
    clicks, set_clicks = react.use_state(0)
    return w.Button(description=f"{label}: Clicked {clicks} times",
                    on_click=lambda: set_clicks(clicks+1))
app = ButtonClick('Ola')
```

Install and run

    $ pip install solara[server]
    $ solara run myapp.py
    INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
    INFO:     Started reloader process [50178] using watchgod
    INFO:     Started server process [50183

The browser should open http://127.0.0.1:8765


# Usage

   * Create a Python script or module and assign an IPywidget instance, or [React-IPywidgets](https://github.com/widgetti/react-ipywidgets) element to the `app` variable.
   * Run the server `$ solara run myapp.py`

Use `solara --help` for help on extra arguments.

## Notebook support

We also support notebooks, simply assign to the app variable in a code cell, save your notebook, and run `$ solara run myapp.ipynb`

# Deployment

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

Note that we explicitly set `--workers 1` such that it does not default to `$WEB_CONCURRENCY` which can be set to higher values, such as on Heroku. See the section on [Caviats](#caviats) why this matters.

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

Note that we explicitly set `--workers 1` such that it does not default to `$WEB_CONCURRENCY` which can be set to higher values, such as on Heroku. See the section on [Caviats](#caviats) why this matters.


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

> :warning: Note that you don't need to install Solara's server dependencies.
 E.g. install `pip install solara`, not `pip install solara[server]`)

Make sure you run a notebook where you display the app, e.g.
```python
@react.component
def MyApp():
    ...
app = MyApp()
display(app)
```

Or consider using [Voila-vuetify](https://github.com/voila-dashboards/voila-vuetify)


## Panel

[Panel](https://panel.holoviz.org/) supports [IPyWidgets](https://panel.holoviz.org/reference/panes/IPyWidget.html), which
means we can also embed the resulting widget from React-IPyWidgets or Solara. See their [section on deployment](https://panel.holoviz.org/user_guide/Server_Deployment.html) and use the following code as an example of how to include a react component.
```python
import panel as pn
import react_ipywidgets as react
import solara as sol


@react.component
def ButtonClick(label="Hi"):
    clicks, set_clicks = react.use_state(0)
    def increment():
        set_clicks(clicks + 1)
    return sol.Button(f"{label}: Clicked {clicks} times", on_click=increment)

# this creates just an element, Panel doesn't know what to do with that
app = ButtonClick("Solara+Panel")
# we explicitly ask React-IPyWidgets to render it, and give us the widget
button_widget, render_context = react.render_fixed(app)
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


## Caviats
Currently, using multiple workers requires sticky sessions on the `solara-context-id` cookie, so that the application context/state is in the same process the user connects to each time. Otherwise different connections may end up talking to different nodes or processes.

We plan to improve this situation in the future. In the meantime, please set your workers to 1, or go through the hassle of setting up multiple Python webservers and make your sessions sticky.



# Installation
## User

Most users:

    $ pip install solara[server,examples]

Conda users (not yet):

    $ conda install -c conda-forge install solara


## Development

If you want to develop on Solara, or you want to run the master branch, you can follow these steps:

First clone the repo:

    $ git clone git@github.com:widgetti/solara.git

Install Solara in 'edit' mode. We use flit (`pip install flit` if you don't already have it)

    $ cd solara
    $ flit install --pth-file --deps develop --extras server,examples

Now you can edit the source code in the git repository, without having to reinstall it.

### Running Solara in dev mode

By passing the `--dev` flag, solara enters "dev" mode, which makes it friendlier for development

    $ solara run myscript.py --dev

Now, if the Solara source code is edited, the server will automatically restart. Also, this enabled the `--mode=development` which will:

   * Load non-minified JS/CSS to make debugging easier
   * Follow symlinks for the nbextensions, enabling the use of widget libraries in development mode.

### Reloading of .vue files

The solara server automatically watches all `.vue` files that are used by vue templates (there are some used in solara.components for example).
When a `.vue` file is saved, the widgets get updated automatically, without needing a page reload, aiding rapid development.

## Contributing

If you plan to contribute, also run the following:

    $ pre-commit install

This will cause a test of linters/formatters and mypy to run so the code is in good quality before you git commit.

    $ playwright install

This will install playwright, for when you want to run the integration tests.

### Test suite

If you want to run the unit tests (quick run when doing development, or when you do test driven development)

    $ py.test tests/unit


If you want to run the integration tests (uses playwright to open a browser to test the live server with a real browser)

    $ py.test tests/integration

Pass the `--headed` flag to see what is going on, [or check out the docs](https://playwright.dev/python/docs/intro)

# FAQ

## I am not interested in the server, I'm happy with Jupyter/Voila, what's in it for me?

That means you simply do not use or install the server component, just use the React-ipywidgets components and run it with Voila.

## Is the Solara server better than Voilà?

No, they are different, and there are situations where I would recommend Voila instead of Solara.

If your app is compute-heavy, and a lot of the compute is happening in pure Python, the GIL (Global Interpreter Lock) can become a bottleneck with Solara, and Voila might give you better performance per client.

If you have a lot of users with short sessions, Solara spares you from having to start up a kernel for each request. Since Solara can use multiple workers in the near future, you can still scale up using multiple processes. Voila will have one process per user, while Solara can share a process with many users.


## Can Solara run a normal Python script?

Yes, this is the preferred way of using Solara. You edit a Python script, save it, Solara will detect the file change and reload the page in your browser (no interaction is needed).

```bash
$ solara myapp.py --dev
INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
INFO:     Started reloader process [50178] using watchgod
INFO:     Started server process [50183

... file change detected ...
(server refreshes, your page will reload)

```

## Can Solara run from a Python package/module?

Over time, when your application becomes larger, you probably want to structure your application into a Python package. Instead of a filename, you pass in the package name on the command line

```bash
$ solara mystartup.killerapp --dev
....
```

## Can Solara run Jupyter notebook?

Yes, Solara will execute each cell, and after that will look for a variable `app`, like with a normal script. All other output, Markdown or other types of cells will be ignored.



## Can I use Solara in my existing FastAPI/Starlette/Flask server?

Yes, take a look at the `solara.server.starlette`  and `solara.server.fastapi` and `solara.server.flask` module. The usage will change over time, so read the source and be ready to change this in the future. We do plan to provide a stable API for this in the future.


## How to fix: inotify watch limit reached?

Add the line

    fs.inotify.max_user_watches=524288

To your /etc/sysctl.conf file, and run `sudo sysctl -p.`

Or if you are using visual studio code, please read: https://code.visualstudio.com/docs/setup/linux#_visual-studio-code-is-unable-to-watch-for-file-changes-in-this-large-workspace-error-enospc
