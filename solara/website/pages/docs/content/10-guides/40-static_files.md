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
import solara


@solara.component
def Page():

    image_url = "/static/public/beach.jpeg"
    with solara.VBox() as main:
        with solara.Card(title="The following image is served from the ../public directory"):
            solara.Image(image_url)
    return main

```
