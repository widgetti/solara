# Tutorial: IPywidgets

If you are already using [ipywidgets](/docs/understanding/ipywidgets) in the notebook, possibly using [Voila](/docs/understanding/voila), you might be pleased to know that you
can also use the [Solara server](/docs/understanding/solara-server) to render your regular ipywidget application.

We recommend you learn how to write applications using [Reacton](/docs/understanding/reacton). However, if you have already written an application in
pure [ipywidgets](/docs/understanding/ipywidgets), this approach will let you gradually move from pure ipywidgets to Reacton.

## You should know
This tutorial will assume you have successfully installed Solara.

If not, please follow the [Installation guide](/docs/installing).

## Your first ipywidget based Solara app

Put the following code in a file called `sol-ipywidgets.py`:

```python
import ipywidgets as widgets

clicks = 0

print("I get run at startup, and for every page request")

def on_click(button):
    global clicks
    clicks += 1
    button.description = f"Clicked {clicks} times"


button = widgets.Button(description="Clicked 0 times")
button.on_click(on_click)
```

And run the following command in your shell
```bash
$ solara run sol-ipywidgets.py:button
Solara server is starting at http://localhost:8765
I get run at startup, and for every page request
...
# your browser opens http://localhost:8765
I get run at startup, and for every page request
...
```

The Solara server will execute your script once before any browser connects,
as demonstrated by the `"I get run at startup, and for every page request"` output.

The `:button` part on the command line tells the Solara server the variable name of
the widget it should render. The default name for a widget variable Solara will look
for is `page`.

For every page request (for instance, you open a second tab, or do a page refresh)
you will see the same text printed out in the terminal.
This tell you that each "tab" gets its own run, and its own namespace, which means
that the `clicks` variable is not shared between multiple users.

If you refresh the page, the script is executed again, and the `clicks` is set to
`0` again.

## Hot reloading

If you edit your script, and save it, Solara server will re-execute it for all connected users without you having to manually refresh your browser.

Try making the following code change (remove the first, add the last), and watch your browser page instantly refresh.
```diff
- button = widgets.Button(description="Clicked 0 times")
+ button = widgets.Button(description="Did not click yet!")
```

## Using Solara components

There are a lot of [valuable components in Solara](/api), but they are written as [Reacton/Solara components](/docs/understanding/reacton-basics), not
classic ipywidgets.

Use the [.widget(...)](/api/widget) method on a component to create a widget that can be used in your existing classic ipywidget application.

```python

import ipywidgets as widgets

import solara

clicks = 0


def on_click(button):
    global clicks
    clicks += 1
    button.description = f"Clicked {clicks} times"


button = widgets.Button(description="Clicked 0 times")
button.on_click(on_click)

page = widgets.VBox(
    [
        button,
        # using .widget(..) we can create a classic ipywidget from a solara component
        solara.FileDownload.widget(data="some text data", filename="solara-demo.txt"),
    ]
)
```

Now we can run this app using:
```
$ solara run sol-ipywidgets.py
```

Note that we did not include the `:page` here, since solara will automatically look for that.

## What you have learned

  * [Solara server](/docs/understanding/solara-server) can render [ipywidgets](/docs/understanding/ipywidgets).
  * Running `$ solara run filename.py:variablename` tells Solara which script to execute and which variable name from the script to render.
  * The script is executed:
    * Once, when the solara server starts.
    * On each page request.
    * For each open browser page/tab, when the script is saved (hot reloading).
  * Using the [.widget(...)](/api/widget) method we can start using Solara components in classic ipywidget app.
