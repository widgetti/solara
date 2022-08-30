# Static files

Static files can be served under `/static/public` and will look for files in the `../public` directory. A typical directory layout looks like this:

```
├── pages
│   ├── 01-landing-page.md
│   ├── 02-some_app.py
└── public
    └── beach.jpeg
```

Putting the `public` directory 1 level higher than the `pages` directory avoids name collision with pages.

```solara
from solara.alias import react, sol

@react.component
def Page():

    image_url = "/static/public/beach.jpeg"
    with sol.VBox() as main:
        with sol.Card(title="The following image is served from the ../public directory"):
            sol.Image(image_url)
    return main

```
