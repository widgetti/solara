# Tutorial: Web app

In this tutorial, you will learn how to use Solara to create a tiny web app using only Python.

## You should know
This tutorial will assume you have successfully installed Solara.

If not, please follow the [Installation guide](/docs/installing).

## Generate a script file
The simplest way to get started is to run the command

```bash
$ solara create button
Wrote:  /Users/maartenbreddels/github/widgetti/solara/sol.py
Run as:
         $ solara run /Users/maartenbreddels/github/widgetti/solara/sol.py
```

This will create the `sol.py` file with the following content.
```solara
import solara

clicks = solara.reactive(0)


@solara.component
def Page():
    color = "green"
    if clicks.value >= 5:
        color = "red"

    def increment():
        clicks.value += 1
        print("clicks", clicks)

    solara.Button(label=f"Clicked: {clicks}", on_click=increment, color=color)
```


## Run the script

Using [Solara server](/docs/understanding/solara-server), we can now run our Python script using:

```bash
$ solara run sol.py
Solara server is starting at http://localhost:8765
```

If you open the URL in your browser ([or click here](http://localhost:8765)), you should see the same example as above.

Solara will run your script once, and will look for the `Page` component. Solara expects this component to exist
and be a [Reacton](/docs/understanding/reacton) component. (See the [IPywidget tutorial](/docs/tutorial/ipywidgets) to learn how to render a regular ipywidget).

Since your script is only run once, you could put in the main body of your script code that only needs to run once (e.g. loading data from disk)

Every browser/user that connects will get an independent version of the state (in this case the number of clicks), so
you do not share the number of clicks with other people.

## Modify the script

Lets modify the script a little bit, possibly in this way:

```diff
-    solara.Button(label=f"Clicked: {clicks}", on_click=increment, color=color)
+    label = "Not clicked yet" if clicks.value == 0 else f"Clicked: {clicks}"
+    solara.Button(label=label, on_click=increment, color=color)
```

If we save the script, Solara will automatically reload your script and update
your browser (we call this feature [hot reloading](/docs/reference/reloading)).

Note that Solara will remember your state (e.g., the number of buttons clicked) when the app reloads.

(*Note: Upgrade to solara 1.14.0 for a fix in hot reloading using `pip install "solara>=1.14.0"`*)

## What you have learned

   * How to create a Python script `sol.py` by running `solara create button`
   * How to run the script with Solara server by running `solara run sol.py`
   * Your script is executed once, which is useful for loading data in the main body of your script only once.
   * Your script should have a component called `Page`.
   * Every user has its own state (in the above example, the number of clicks)
   * If you save your script, Solara will automatically re-execute your script, and all attached users will see the changes directly (hot reloading).
