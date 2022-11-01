# This title is not used

We use the filename for the title.

```python
this = "renders to highlighted Python code
```


## Embed a solara example

This renders highlighted Python code, and shows app.
```solara
import solara


@solara.component
def ClickButton():
    clicks, set_clicks = solara.use_state(0)

    color = "green"
    if clicks >= 5:
        color = "red"

    def on_click():
        set_clicks(clicks + 1)
        print("clicks", clicks)

    return solara.Button(label=f"Clicked: {clicks}", on_click=on_click, color=color)


app = ClickButton()
