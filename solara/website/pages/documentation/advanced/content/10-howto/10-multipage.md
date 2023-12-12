# Multi-page support

In the [Web App tutorial](/docs/tutorial/web-app), we created an application consisting of a single page. Web applications generally have multiple pages, and Solara supports this as well.


## Multiple scripts

The simplest way to create a multi-page app is to create a directory with multiple scripts.

```bash
$ solara create button multipage-demo/01-click-button.py
Wrote:  /mypath/multipage-demo/01-click-button.py
...
$ solara create markdown multipage-demo/02-markdown-editor.py
Wrote:  /mypath/multipage-demo/02-markdown-editor.py
...
```


You should have the following directory structure:

```
multipage-demo
├── 01-click-button.py
└── 02-markdown-editor.py
```

Now run Solara, with this directory as argument:

```bash
$ solara run ./multipage-demo
Solara server is starting at http://localhost:8765
```

Giving you an output like:

![screencapture](https://user-images.githubusercontent.com/1765949/214879312-19323de3-c4ce-4528-ac84-5aa0021ca5b4.gif)

Solara now:

   * Sort the paths according to the filename (hence the 01- and 02- prefix)
   * Generate a nice URL by stripping of prefix, splitting the filename taking out `-`, `_` and spaces, and join them together using a `-`  (e.g. "/markdown-editor").
   * Generate a nice default title similar to the link, but now capitalize the first letter and join with a space instead  (e.g. "Mardown Editor").
   * The first page will be the default (and its URL will be empty instead, i.e., the empty string `""`)
   * Since the first script does not define a `Layout` component, nor did we add a `__init__.py` with a `Layout` component, Solara will add a [default
     Layout component](/api/default_layout) which includes a navigation sidebar.
   * If a path is a directory, Solara will recursively scan the subdirectory and include it in the navigation. Read more on this in the [Layout section](layout)

Solara will render two pages:

   * http://localhost:8765 with title "Click Button"
   * http://localhost:8765/markdown-editor with title "Markdown Editor"



## Classical widgets support

Multipage is also supported for regular ipywidgets.  An example directory can be seen on [GitHub](https://github.com/widgetti/solara/tree/master/tests/unit/solara_test_apps/multipage),
which we use for testing.

A large difference between using regular ipywidgets for pages compared to using components is that there is no lifecycle
management in regular ipywidgets. This means Solara cannot clean up your ipywidget-based page (garbage-collect the unused widgets, unregister callbacks)
when a user navigates away from your page.

At the same time, rerunning your regular ipywidget-based script each time a user navigates to that page will result in a buildup of many widgets.

This means that Solara will run your page once (the first time it is loaded by a user/browser tab), and, when navigating back,
will show the page in the same state as when the user left the page.


## As a package

Once you start building a larger application, it pays off using a Python package instead. This allows you to organize and distribute your app as a Python package (as a wheel for instance) and allows you to organize your application
into reusable packages for components, stores, hooks etc.

As a quickstart, we can generate a startup project using:
```bash
$ solara create portal solara-test-portal
Wrote:  /Users/maartenbreddels/github/widgetti/solara/solara-test-portal
Install as:
         $ (cd solara-test-portal; pip install -e .)
Run as:
         $ solara run solara_test_portal.pages
```

You should have the following directory structure:
```bash
├── LICENSE
├── Procfile # will make it run on heroku
├── mypy.ini # adds strict type checking
├── pyproject.toml  # make it installable with pip/hatch etc
└── solara_test_portal  # Python package containing all code
    ├── __init__.py
    ├── components # contains general react components
    │   ├── __init__.py
    │   ├── header.py
    │   └── layout.py
    ├── content  # contains content (markdown articles in this case)
    │   └── articles
    │       ├── 7-reasons-why-i-love-vaex-for-data-science.md
    │       └── a-hybrid-apache-arrow-numpy-dataframe-with-vaex-version-4.md
    ├── data.py  # here is where we store shared data or application state
    └── pages  # contains the pages
        ├── __init__.py
        ├── article
        │   └── __init__.py
        ├── tabular.py
        └── viz
            ├── __init__.py
            └── overview.py
```

Install it using
```bash
$ (cd solara-test-portal; pip install -e .)
```

Run it with
```bash
$ solara run solara_test_portal.pages
Solara server is starting at http://localhost:8765
```

Go to http://localhost:8765 ([or click here](http://localhost:8765)), explore the source code, edit it, save it, and watch the web app reload instantly.


## In a single script

If you want to setup a multipage app in a single script, you do not need to define a `Page` component, but you can define a list of routes.

```python
import solara


@solara.component
def Home():
    solara.Markdown("Home")


@solara.component
def About():
    solara.Markdown("About")


routes = [
    solara.Route(path="/", component=Home, label="home"),
    solara.Route(path="about", component=About, label="about"),
]
```

See more details in the [Route section](/docs/understanding/routing).

## Dynamic pages

In the previous section we created the example portal app. Taking a look at
tabular.py, we see the `Page` component takes an additional arguments.

```python
@solara.component
def Page(name: str):
    ...
```


Solara recognizes this and will pass all routes such as `/tabular/foo` and `/tabular/bar` to this Page component passing for instance `"foo"` or `"bar"` as an argument, such that you can dynamically render a page based on the URL.

An example Page component could look like this:

```python
@solara.component
def Page(name: str = "foo"):
    subpages = ["foo", "bar", "solara", "react-ipywidgets"]
    solara.Markdown(f"You are at: {name}")
    # bunch of buttons which navigate to our dynamic route
    with solara.Row():
        for subpage in subpages:
            with solara.Link(subpage):
                solara.Button(label=f"Go to: {subpage}")
```

By giving the name argument a default value of `"foo"`, Solara will also accept the `/tabular` url.

# What you have learned

  * Putting multiple Solara app script into a directory allows Solara to show a multipage app.
  * If no `Layout` component is provided, Solara adds a default navigation sidebar.
  * Large application can benefit from setting up a Python package, use `solara create portal my-name` to create one.
  * By adding an argument to the `Page` component, routes like `/tabular` will turn into dynamic routes (e.g. `/tabular/dynamic-name`) and pass the argument (`"dynamic-name"` in this case) to the `Page` component to implement dynamic pages.

# What next?

  * Also check out the [Multipage example](/apps/multipage) for more inspiration.
