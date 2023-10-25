import datetime as dt
from unittest.mock import MagicMock

# import ipyvuetify as vw
from playwright.sync_api import Page  # , expect

today = dt.date.today()
tomorrow = today + dt.timedelta(days=1)


def test_input_date_range_managed(solara_test, page_session: Page):
    import solara
    from solara.lab import InputDateRange

    on_value = MagicMock()

    @solara.component
    def Page():
        def update_value(value: float):
            on_value(value)
            set_value(value)

        value, set_value = solara.use_state([today, tomorrow])
        InputDateRange(value=value, label="label", on_value=update_value)

    solara.display(Page())
