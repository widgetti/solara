# The dashboard app without Vuetify components: an own Layout with links, an HTML table,
# a template-only VueTemplate slider and Markdown without math or diagrams.
# The slider template has no <script setup>, no scoped style and no lang="ts",
# so it does not need the vue-sfc feature.
import html

import ipyvue
import numpy as np
import pandas as pd
import traitlets

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


class RangeSlider(ipyvue.VueTemplate):
    template = traitlets.Unicode(
        """
<template>
  <label>
    Rows
    <input type="range" min="1" max="200" v-model.number="value" />
    {{ value }}
  </label>
</template>
"""
    ).tag(sync=True)
    value = traitlets.Int(50).tag(sync=True)


def table_html(frame: pd.DataFrame) -> str:
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in frame.columns)
    rows = "".join("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row) + "</tr>" for row in frame.itertuples(index=False))
    return f"<thead><tr>{head}</tr></thead><tbody>{rows}</tbody>"


@solara.component
def Home():
    solara.Markdown("# Data page\nA small synthetic frame.")
    RangeSlider.element(value=n.value, on_value=n.set)
    solara.HTML(tag="table", unsafe_innerHTML=table_html(df.head(min(n.value, 10))))


@solara.component
def About():
    solara.Markdown("# About\nThe second page.")


routes = [
    solara.Route(path="/", component=Home, label="Home"),
    solara.Route(path="about", component=About, label="About"),
]


@solara.component
def Layout(children=[]):
    with solara.Column() as main:
        solara.Link("/", children=["Home"])
        solara.Link("/about", children=["About"])
        solara.Column(children=children)
    return main
