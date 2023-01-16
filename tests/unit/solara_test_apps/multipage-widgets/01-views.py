import ipywidgets as widgets

clicks = 0

print("View button: I get run at startup, and for every page request")  # noqa


def on_click(button):
    global clicks
    clicks += 1
    button.description = f"Viewed {clicks} times"


button = widgets.Button(description="Never viewed")
button.on_click(on_click)

page = button
