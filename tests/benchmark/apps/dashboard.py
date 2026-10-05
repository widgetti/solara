# A typical small app: AppLayout, 2 routes, a slider, a DataFrame with fake data and Markdown.
import numpy as np
import pandas as pd

import solara

rng = np.random.default_rng(42)
df = pd.DataFrame(
    {
        "name": [f"row-{i}" for i in range(200)],
        "x": rng.normal(size=200).round(3),
        "y": rng.integers(0, 100, size=200),
        "cat": rng.choice(["a", "b", "c"], size=200),
    }
)
n = solara.reactive(50)


@solara.component
def Home():
    solara.Markdown("# Data page\nA small synthetic frame.")
    solara.SliderInt("Rows", value=n, min=1, max=200)
    solara.DataFrame(df.head(n.value), items_per_page=10)


@solara.component
def About():
    solara.Markdown("# About\nThe second page.")


routes = [
    solara.Route(path="/", component=Home, label="Home"),
    solara.Route(path="about", component=About, label="About"),
]


@solara.component
def Layout(children=[]):
    return solara.AppLayout(children=children, title="Demo")
