# Static files

Files located on your local filesystem at the `../public` directory will be served by the Solara server at `/static/public`. A typical directory layout looks like this:

```
├── pages
│   ├── 01-landing-page.md
│   ├── 02-some_app.py
└── public
    └── beach.jpeg
```

For instance, on this server, the `beach.jpeg` file will be available at `/static/public/beach.jpeg` and the full URL will be [`https://solara.dev/static/public/beach.jpeg`](https://solara.dev/static/public/beach.jpeg)

Putting the `public` directory 1 level higher than the `pages` directory avoids name collision with pages.

```solara
import solara


@solara.component
def Page():
    image_url = "/static/public/beach.jpeg"
    with solara.Card(title="The following image is served from the ../public directory"):
        solara.Image(image_url)

```
