import ipywidgets as widgets

clicks = 0


def on_click(button):
    global clicks
    clicks += 1
    button.description = f"Clicked {clicks} times"


button = widgets.Button(description="Clicked 0 times")
button.on_click(on_click)
