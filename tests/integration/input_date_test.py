import datetime as dt
from typing import List
from unittest.mock import MagicMock

from playwright.sync_api import Page, expect

date = dt.date(2018, 9, 1)
date2 = date + dt.timedelta(days=1)


def test_input_date_single(solara_test, page_session: Page):
    import solara
    from solara.lab import InputDate

    on_value = MagicMock()

    @solara.component
    def Page():
        def update_value(value: dt.date):
            on_value(value)
            set_value(value)

        value, set_value = solara.use_state(date)
        InputDate(value=value, label="label", on_value=update_value, classes=["test-class"])

    solara.display(Page())

    input = page_session.locator(".test-class input")
    expect(input).to_be_visible()
    expect(input).to_have_value(date.strftime("%Y/%m/%d"))
    input.click()
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).to_be_visible()
    today_button = page_session.get_by_role("button", name=date.strftime("%-d"), exact=True)
    # We click it, but it does not trigger a change, so we don't auto close
    # Do we want to change this behaviour, and still close it?
    today_button.click()
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).to_be_visible()
    tomorrow_button = page_session.get_by_role("button", name=date2.strftime("%-d"), exact=True)
    tomorrow_button.click()
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).not_to_be_visible()

    input.click()
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).to_be_visible()
    page_session.mouse.click(400, 400)
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).not_to_be_visible()

    page_session.wait_for_timeout(350)
    input.click()
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).to_be_visible()
    page_session.keyboard.press("Tab")
    expect(page_session.get_by_role("menu")).not_to_be_visible()


def test_input_date_range(solara_test, page_session: Page):
    import solara
    from solara.lab import InputDateRange

    on_value = MagicMock()

    @solara.component
    def Page():
        def update_value(value: List[dt.date]):
            on_value(value)
            set_value(value)

        value, set_value = solara.use_state([date, date2])
        InputDateRange(value=value, label="label", on_value=update_value, classes=["test-class"])

    solara.display(Page())

    input = page_session.locator(".test-class input")
    expect(input).to_be_visible()
    expect(input).to_have_value(f"{date.strftime('%Y/%m/%d')} - {date2.strftime('%Y/%m/%d')}")
    input.click()
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).to_be_visible()
    today_button = page_session.get_by_role("button", name=date.strftime("%-d"), exact=True)
    today_button.click()
    page_session.wait_for_timeout(350)
    expect(page_session.locator(".test-class label")).to_contain_text("label (Please select two dates)")
    expect(page_session.get_by_role("menu")).to_be_visible()
    tomorrow_button = page_session.get_by_role("button", name=date2.strftime("%-d"), exact=True)
    tomorrow_button.click()
    page_session.wait_for_timeout(350)
    expect(page_session.locator(".test-class label")).not_to_contain_text("(Please select two dates)")
    expect(page_session.get_by_role("menu")).not_to_be_visible()
    input.click()
    page_session.mouse.click(400, 400)
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).not_to_be_visible()

    page_session.wait_for_timeout(350)
    input.click()
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).to_be_visible()
    page_session.keyboard.press("Tab")
    expect(page_session.get_by_role("menu")).not_to_be_visible()
