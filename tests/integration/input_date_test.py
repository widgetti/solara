import datetime as dt
import re
from typing import List
from unittest.mock import MagicMock

from playwright.sync_api import Page, expect

from solara.util import IPYVUETIFY_V3


def menu_of(page: Page):
    # vuetify 3 does not put role=menu on the overlay content like vuetify 2 did
    return page.locator(".v-overlay__content") if IPYVUETIFY_V3 else page.get_by_role("menu")


def dismiss_menu(page: Page):
    # the vuetify 3 picker is larger and covers the point the vuetify 2 test
    # clicks, and its menu has no scrim to click through, so close it with the
    # keyboard there
    if IPYVUETIFY_V3:
        page.keyboard.press("Escape")
    else:
        page.mouse.click(400, 400)


def label_of(page: Page):
    # vuetify 3 renders a floating label and an aria-hidden one; keep the strict
    # locator on vuetify 2, where there is exactly one
    label = page.locator(".test-class label")
    return label.first if IPYVUETIFY_V3 else label


def day_button(page: Page, day: str):
    # vuetify 3 labels the day buttons with the full date ("Wednesday, January
    # 1, 2024"), so the accessible name is never just the day number
    if IPYVUETIFY_V3:
        return page.locator(".v-date-picker-month__day-btn").filter(has_text=re.compile(rf"^{day}$"))
    return page.get_by_role("button", name=day, exact=True)


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
    expect(menu_of(page_session)).to_be_visible()
    today_button = day_button(page_session, date.strftime("%d").lstrip("0"))
    # We click it, but it does not trigger a change, so we don't auto close
    # Do we want to change this behaviour, and still close it?
    today_button.click()
    page_session.wait_for_timeout(350)
    expect(menu_of(page_session)).to_be_visible()
    tomorrow_button = day_button(page_session, date2.strftime("%d").lstrip("0"))
    tomorrow_button.click()
    page_session.wait_for_timeout(350)
    expect(menu_of(page_session)).not_to_be_visible()

    input.click()
    page_session.wait_for_timeout(350)
    expect(menu_of(page_session)).to_be_visible()
    dismiss_menu(page_session)
    page_session.wait_for_timeout(350)
    expect(menu_of(page_session)).not_to_be_visible()

    page_session.wait_for_timeout(350)
    input.click()
    page_session.wait_for_timeout(350)
    expect(menu_of(page_session)).to_be_visible()
    page_session.keyboard.press("Tab")
    expect(menu_of(page_session)).not_to_be_visible()


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
    expect(menu_of(page_session)).to_be_visible()
    today_button = day_button(page_session, date.strftime("%d").lstrip("0"))
    today_button.click()
    page_session.wait_for_timeout(350)
    expect(label_of(page_session)).to_contain_text("label (Please select two dates)")
    expect(menu_of(page_session)).to_be_visible()
    tomorrow_button = day_button(page_session, date2.strftime("%d").lstrip("0"))
    tomorrow_button.click()
    page_session.wait_for_timeout(350)
    expect(label_of(page_session)).not_to_contain_text("(Please select two dates)")
    expect(menu_of(page_session)).not_to_be_visible()
    input.click()
    dismiss_menu(page_session)
    page_session.wait_for_timeout(350)
    expect(menu_of(page_session)).not_to_be_visible()

    page_session.wait_for_timeout(350)
    input.click()
    page_session.wait_for_timeout(350)
    expect(menu_of(page_session)).to_be_visible()
    page_session.keyboard.press("Tab")
    expect(menu_of(page_session)).not_to_be_visible()
