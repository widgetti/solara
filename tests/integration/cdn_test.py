import playwright.sync_api
import pytest
from IPython.display import display

from .conftest import SERVERS

# the altair figure uses the CDN


def test_cdn_via_altair(ipywidgets_runner, page_session: playwright.sync_api.Page, request, assert_solara_snapshot):
    if request.node.callspec.params["ipywidgets_runner"] != "solara" and request.node.callspec.params["solara_server"] != SERVERS[0]:
        pytest.skip("No need to run this test for all servers.")

    # this function (or rather its lines) will be executed in the kernel
    # voila, lab, classic notebook and solara will all execute it
    def kernel_code():
        import altair as alt
        from vega_datasets import data

        import solara

        source = data.seattle_weather()

        @solara.component
        def Page():
            chart = (
                alt.Chart(source, title="Daily Max Temperatures (C) in Seattle, WA")
                .mark_rect()
                .encode(
                    alt.X("date(date):O").title("Day").axis(format="%e", labelAngle=0),
                    alt.Y("month(date):O").title("Month"),
                    alt.Color("max(temp_max)").title(None),
                    tooltip=[
                        alt.Tooltip("monthdate(date)", title="Date"),
                        alt.Tooltip("max(temp_max)", title="Max Temp"),
                    ],
                )
                .configure_view(step=13, strokeWidth=0)
                .configure_axis(domain=False)
            )
            solara.AltairChart(chart)

        display(Page())

    ipywidgets_runner(kernel_code)
    vega_selector = page_session.locator('details[title="Click to view actions"]')
    vega_selector.wait_for(state="attached")
    # assert_solara_snapshot(vega_selector.screenshot())
    # page_session.wait_for_timeout(1000)
