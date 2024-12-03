"""Demonstrates very basic usage of Solara."""

import solara

redirect = None


@solara.component
def Page():
    return solara.Markdown("Should not see me")
