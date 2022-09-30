"""
# Slider

To support proper typechecks, we have multiple slider (all wrapping the ipyvuetify slider).
"""
import datetime

import solara


@solara.component
def Page():
    with solara.VBox() as main:
        with solara.Card("Integers"):
            int_value, set_int_value = solara.use_state(42)
            solara.IntSlider("Some integer", value=int_value, min=-10, max=120, on_value=set_int_value)
            solara.Markdown(f"**Int value**: {int_value}")

        with solara.Card("Floats"):
            float_value, set_float_value = solara.use_state(42.4)
            solara.FloatSlider("Some float", value=float_value, min=-10, max=120, on_value=set_float_value)
            solara.Markdown(f"**Float value**: {float_value}")

        with solara.Card("Values"):
            values = "Python C++ Java JavaScript TypeScript BASIC".split()
            value, set_value = solara.use_state(values[0])
            solara.ValueSlider("Language", value, values=values, on_value=set_value)
            solara.Markdown(f"**Value**: {value}")

        with solara.Card("Dates"):
            date, set_date = solara.use_state(datetime.date(1981, 7, 28))
            solara.DateSlider("Some date", value=date, on_value=set_date)
            solara.Markdown(f"**Date**: {date.strftime('%Y-%b-%d')}")

    return main
