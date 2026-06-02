import datetime as dt
from typing import List
from unittest.mock import MagicMock

from playwright.sync_api import Page, expect

date = dt.date(2018, 9, 1)
date2 = date + dt.timedelta(days=1)
date3 = date + dt.timedelta(days=2)


def date_picker_popup(page: Page):
    return page.locator('[role="menu"], [role="listbox"]')


def input_label(page: Page):
    return page.locator(".test-class label:not([aria-hidden='true'])")


def apply_date_picker(page: Page):
    ok_button = page.get_by_role("button", name="OK", exact=True)
    if ok_button.count():
        ok_button.click()


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
    expect(date_picker_popup(page_session)).to_be_visible()
    today_button = page_session.get_by_role("button", name=date.strftime("%d").lstrip("0"), exact=True)
    # We click it, but it does not trigger a change, so we don't auto close
    # Do we want to change this behaviour, and still close it?
    today_button.click()
    page_session.wait_for_timeout(350)
    expect(date_picker_popup(page_session)).to_be_visible()
    tomorrow_button = page_session.get_by_role("button", name=date2.strftime("%d").lstrip("0"), exact=True)
    tomorrow_button.click()
    apply_date_picker(page_session)
    page_session.wait_for_timeout(350)
    expect(date_picker_popup(page_session)).not_to_be_visible()

    input.click()
    page_session.wait_for_timeout(350)
    expect(date_picker_popup(page_session)).to_be_visible()
    page_session.mouse.click(10, 10)
    page_session.wait_for_timeout(350)
    expect(date_picker_popup(page_session)).not_to_be_visible()

    page_session.wait_for_timeout(350)
    input.click()
    page_session.wait_for_timeout(350)
    expect(date_picker_popup(page_session)).to_be_visible()
    page_session.keyboard.press("Tab")
    expect(date_picker_popup(page_session)).not_to_be_visible()


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
    expect(date_picker_popup(page_session)).to_be_visible()
    today_button = page_session.get_by_role("button", name=date.strftime("%d").lstrip("0"), exact=True)
    today_button.click()
    page_session.wait_for_timeout(350)
    expect(input_label(page_session)).to_contain_text("label")
    expect(date_picker_popup(page_session)).to_be_visible()
    third_day_button = page_session.get_by_role("button", name=date3.strftime("%d").lstrip("0"), exact=True)
    third_day_button.click()
    apply_date_picker(page_session)
    page_session.wait_for_timeout(350)
    expect(input_label(page_session)).not_to_contain_text("(Please select two dates)")
    expect(date_picker_popup(page_session)).not_to_be_visible()
    input.click()
    page_session.mouse.click(10, 10)
    page_session.wait_for_timeout(350)
    expect(date_picker_popup(page_session)).not_to_be_visible()

    page_session.wait_for_timeout(350)
    input.click()
    page_session.wait_for_timeout(350)
    expect(date_picker_popup(page_session)).to_be_visible()
    page_session.keyboard.press("Tab")
    expect(date_picker_popup(page_session)).not_to_be_visible()
