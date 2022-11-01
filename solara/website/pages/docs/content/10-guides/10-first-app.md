# Your first Solara app


## Generate a script file
The simplest way to get started is to run the command

```bash
$ solara create button
Wrote:  /Users/maartenbreddels/github/widgetti/solara/sol.py
Run as:
         $ solara run /Users/maartenbreddels/github/widgetti/solara/sol.py
```

This will create the file `sol.py` with the following content.
```solara
import solara


@solara.component
def Page():
    clicks, set_clicks = solara.use_state(0)

    color = "green"
    if clicks >= 5:
        color = "red"

    def on_click():
        set_clicks(clicks + 1)
        print("clicks", clicks)

    return solara.Button(label=f"Clicked: {clicks}", on_click=on_click, color=color)
```


## Run the script

Using solara server, we can now run the script using:

```bash
$ solara run sol.py
Solara server is starting at http://localhost:8765
```

If you open the URL in your browser ([or click here](http://localhost:8765)), you should see the same example as above.

Solara will run your script once, and will look for the `Page` component. Solara expects this component to exist
and be a `reacton` component (or an element, or even a pure `ipywidgets` widget instance).

Since your script is only run once, you could put in the main body of your script code that only needs to run once (e.g. loading data from disk)

Every browser/user that connects will get an independant version of the state (in this case the number of clicks), so
you do not share the number of clicks with other people.

## Modify the script

Lets modify the script a little bit, possibly in this way:

```diff
-    return solara.Button(label=f"Clicked: {clicks}", on_click=on_click, color=color)
+    label = "Not clicked yet" if clicks == 0 else f"Clicked: {clicks}"
+    return solara.Button(label=label, on_click=on_click, color=color)
```

If we now save the script, Solara will automatically reload your script and update
your browser (we call this feature hot reloading).

Note that Solara will remember your state (e.g. the number of buttons clicked) when the app reloads.

# What you have leared

   * How to create a Python script `sol.py` by running `solara create button`
   * How to run the script with Solara server by running `solara run sol.py`
   * Your script is executed once, useful for loading data in the main body of your script only once.
   * Your script should have a component called `Page` (although element and widgets are also supported).
   * Every user has its own state (in the above example, the number of clicks)
   * If you save your script, Solara will automatically re-execute your script, and all attached users will see the changes directly (hot reloading).
