import ipywidgets as widgets

clicks = 0

print("Like button: I get run at startup, and for every page request")  # noqa


def on_click(button):
    global clicks
    clicks += 1
    button.description = f"Liked {clicks} times"


button = widgets.Button(description="No likes recorded")
button.on_click(on_click)

page = button
