
# Debugging

## PDB

You can use the [python debugger](https://docs.python.org/3/library/pdb.html) to debug your Solara app.

Simply add `breakpoint()` to your code, and trigger the code, and you will enter the debugger.

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
        # this will trigger the debugger
        breakpoint()
        print("clicks", clicks)  # noqa

    solara.Button(label=f"Clicked: {clicks}", on_click=increment, color=color)
```

## PyCharm or IntelliJ

You can also use the debugger of PyCharm or IntelliJ to debug your Solara app.
The following settings works for PyCharm or IntelliJ:

![](https://dxhl76zpt6fap.cloudfront.net/public/docs/howto/debugger-intellij.webp)

## VSCode


In VSCode, you can use the following launch.json to debug your Solara app:

```json
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Solara: Launch",
            "type": "python",
            "request": "launch",
            "program": "/Users/maartenbreddels/miniconda3/envs/dev/bin/solara",
            "args": [
                "run",
                "${file}"
            ],
            "console": "integratedTerminal",
            "justMyCode": true,
        }
    ]
}
```

Now keep your script tab open, and press F5 to start debugging (or click the play icon in the UI).
