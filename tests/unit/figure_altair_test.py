import unittest.mock

import pytest

import solara
import solara.widgets


class MockChart:
    """Mock Altair chart that returns a configurable mimebundle."""

    def __init__(self, bundle):
        self._bundle = bundle

    def _repr_mimebundle_(self):
        return (self._bundle, {})


@pytest.fixture
def mock_altair_renderers():
    """Mock altair.renderers.enable to be a no-op context manager."""
    import contextlib

    import altair as alt

    @contextlib.contextmanager
    def mock_enable(renderer):
        yield

    with unittest.mock.patch.object(alt.renderers, "enable", mock_enable):
        yield


def test_figure_altair_v4(mock_altair_renderers):
    spec = {"$schema": "https://vega.github.io/schema/vega-lite/v4.json", "data": {"values": []}}
    chart = MockChart({"application/vnd.vegalite.v4+json": spec})

    el = solara.FigureAltair(chart)
    _, rc = solara.render(el, handle_error=False)
    widget = rc.find(solara.widgets.VegaLite).widget
    assert widget.spec == spec
    rc.close()


def test_figure_altair_v5(mock_altair_renderers):
    spec = {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "data": {"values": []}}
    chart = MockChart({"application/vnd.vegalite.v5+json": spec})

    el = solara.FigureAltair(chart)
    _, rc = solara.render(el, handle_error=False)
    widget = rc.find(solara.widgets.VegaLite).widget
    assert widget.spec == spec
    rc.close()


def test_figure_altair_v6(mock_altair_renderers):
    """Test that Altair 6+ with v6 MIME type works (uses .json suffix instead of +json)."""
    spec = {"$schema": "https://vega.github.io/schema/vega-lite/v6.json", "data": {"values": []}}
    # Altair 6 uses ".json" suffix instead of "+json"
    chart = MockChart({"application/vnd.vegalite.v6.json": spec})

    el = solara.FigureAltair(chart)
    _, rc = solara.render(el, handle_error=False)
    widget = rc.find(solara.widgets.VegaLite).widget
    assert widget.spec == spec
    rc.close()


def test_figure_altair_no_vegalite_mime(mock_altair_renderers):
    """Test that a KeyError is raised when no Vega-Lite MIME type is found."""
    chart = MockChart({"text/plain": "some text"})

    el = solara.FigureAltair(chart)
    with pytest.raises(KeyError, match="No Vega-Lite MIME type found"):
        solara.render(el, handle_error=False)
