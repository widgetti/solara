# Making IPywidgets based web applications simple and fun

![logo](https://user-images.githubusercontent.com/1765949/159178788-2c20214d-d4fe-42cd-a28e-7097ce37c904.svg)

## What is it?

If you only care about using Solara from the Jupyter notebook (classic or lab) or Voila, it is:

   * A set of composable components build on [React-IPywidgets](https://github.com/widgetti/react-ipywidgets) (e.g., Image, Markdown, FileBrowser, etcetera) to get that 'all batteries included' feeling.

If you also want to develop and deploy a more extensive application and prefer not to program in a Jupyter notebook, or care about scaling your application, Solara is also:
   * An application server to make development easier:
       * Auto reloading refreshes the page when you save your script or Jupyter notebook.
       * Your app state is restored after reload/restart: All tabs, checkboxes, etcetera will be as you set them.
   * An application server that:
      * Runs on Starlette (used in FastAPI).
      * Executes:
         * Python scripts
         * Python modules/packages
         * Jupyter notebooks
   * An alternative for Voila, for when:
     * You only need to display widgets
     * One kernel/process per request is becoming a bottleneck/cost issue.
     * Only care about using Python (e.g., not Julia, R)
     * Are ok, or even prefers, to have your application code run in the same process as your web server (e.g., FastAPI, Starlette)



## Example


Create a file `myapp.py`:
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

    $ pip install solara
    $ solara myapp.py
    INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
    INFO:     Started reloader process [50178] using watchgod
    INFO:     Started server process [50183

The browser should open http://127.0.0.1:8765


# Usage

   * Create a Python script or module and assign an IPywidget instance, or [React-IPywidgets](https://github.com/widgetti/react-ipywidgets) element to the `app` variable.
   * Run the server `$ solara myapp.py`
   * Or run in in dev mode for auto reload `$ solara myapp.py --dev`

Use `solara --help` for help on extra arguments.

# Deployment

Currently, using multiple workers requires sticky sessions on the `solara-context-id` cookie, so that the application context/state is in the same process the user connects to each time. Otherwise different connections may end up talking to different nodes or processes.

# How does Solara work?


# Installation
## User

Most users:

    $ pip install solara[server,examples]

Conda users (not yet):

    $ conda install -c conda-forge install solara


## Development

We use flit (`pip install flit` if you don't already have it)

    $ flit install --symlink --deps develop --extras server,examples



# FAQ

## I am not interested in the server, I'm happy with Jupyter/Voila, what's in it for me?

If you enjoy using

## Is the Solara server better than Voilà?

No, they are different, and there are situations where I would recommend Voila instead of Solara.

If your app is compute-heavy, and a lot of the compute is happening in pure Python, the GIL (Global Interpreter Lock) can become a bottleneck with Solara, and Voila might give you better performance per client.

If you have a lot of users with short sessions, Solara spares you from having to start up a kernel for each request. Since Solara can use multiple workers, you can still scale up using multiple processes. Voila will have one process per user, while Solara can share a process with many users.


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



## Can I use Solara in my existing FastAPI/Starlette server?

Yes, take a look at the `solara.server.fastapi` module. The usage will change over time, so read the source and be ready to change this in the future. We do plan to provide a stable API for this in the future.
