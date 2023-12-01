import datetime as dt
from unittest.mock import MagicMock

from playwright.sync_api import Page, expect

today = dt.date.today()
tomorrow = today + dt.timedelta(days=1)


def test_input_date_single(solara_test, page_session: Page):
    import solara
    from solara.lab import InputDate

    on_value = MagicMock()

    @solara.component
    def Page():
        def update_value(value: float):
            on_value(value)
            set_value(value)

        value, set_value = solara.use_state(today)
        InputDate(value=value, label="label", on_value=update_value, classes=["test-class"])

    solara.display(Page())

    input = page_session.locator(".test-class input")
    expect(input).to_be_visible()
    expect(input).to_have_value(today.strftime("%Y/%m/%d"))
    input.click()
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).to_be_visible()
    today_button = page_session.get_by_role("button", name=today.strftime("%-d"), exact=True)
    # We click it, but it does not trigger a change, so we don't auto close
    # Do we want to change this behaviour, and still close it?
    today_button.click()
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).to_be_visible()
    tomorrow_button = page_session.get_by_role("button", name=tomorrow.strftime("%-d"), exact=True)
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
        def update_value(value: float):
            on_value(value)
            set_value(value)

        value, set_value = solara.use_state([today, tomorrow])
        InputDateRange(value=value, label="label", on_value=update_value, classes=["test-class"])

    solara.display(Page())

    input = page_session.locator(".test-class input")
    expect(input).to_be_visible()
    expect(input).to_have_value(f"{today.strftime('%Y/%m/%d')} - {tomorrow.strftime('%Y/%m/%d')}")
    input.click()
    page_session.wait_for_timeout(350)
    expect(page_session.get_by_role("menu")).to_be_visible()
    today_button = page_session.get_by_role("button", name=today.strftime("%-d"), exact=True)
    today_button.click()
    page_session.wait_for_timeout(350)
    expect(page_session.locator(".test-class label")).to_contain_text("label (Please select two dates)")
    expect(page_session.get_by_role("menu")).to_be_visible()
    tomorrow_button = page_session.get_by_role("button", name=tomorrow.strftime("%-d"), exact=True)
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
