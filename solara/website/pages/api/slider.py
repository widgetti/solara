"""
# Sliders

To support proper typechecks, we have multiple slider (all wrapping the ipyvuetify sliders).


"""
import datetime

import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    with solara.VBox() as main:
        with solara.Card("Integer"):
            int_value, set_int_value = solara.use_state(42)
            solara.SliderInt("Some integer", value=int_value, min=-10, max=120, on_value=set_int_value)
            solara.Markdown(f"**Int value**: {int_value}")

        with solara.Card("Integer range"):
            int_range_value, set_int_range_value = solara.use_state((0, 42))
            solara.SliderRangeInt("Some integer range", value=int_range_value, min=-10, max=120, on_value=set_int_range_value)
            solara.Markdown(f"**Int range value**: {int_range_value}")

        with solara.Card("Float"):
            float_value, set_float_value = solara.use_state(42.4)
            solara.SliderFloat("Some float", value=float_value, min=-10, max=120, on_value=set_float_value)
            solara.Markdown(f"**Float value**: {float_value}")

        with solara.Card("Float range"):
            float_range_value, set_float_range_value = solara.use_state((0.1, 42.4))
            solara.SliderRangeFloat("Some float", value=float_range_value, min=-10, max=120, on_value=set_float_range_value)
            solara.Markdown(f"**Float value**: {float_range_value}")

        with solara.Card("Values"):
            values = "Python C++ Java JavaScript TypeScript BASIC".split()
            value, set_value = solara.use_state(values[0])
            solara.SliderValue("Language", value, values=values, on_value=set_value)
            solara.Markdown(f"**Value**: {value}")

        with solara.Card("Dates"):
            date, set_date = solara.use_state(datetime.date(1981, 7, 28))
            solara.SliderDate("Some date", value=date, on_value=set_date)
            solara.Markdown(f"**Date**: {date.strftime('%Y-%b-%d')}")

    return main


__doc__ += "# SliderInt"
__doc__ += apidoc(solara.SliderInt.f)  # type: ignore
__doc__ += "# SliderRangeInt"
__doc__ += apidoc(solara.SliderRangeInt.f)  # type: ignore

__doc__ += "# SliderFloat"
__doc__ += apidoc(solara.SliderFloat.f)  # type: ignore
__doc__ += "# SliderRangeFloat"
__doc__ += apidoc(solara.SliderRangeFloat.f)  # type: ignore

__doc__ += "# SliderValue"
__doc__ += apidoc(solara.SliderValue.f)  # type: ignore

__doc__ += "# SliderDate"
__doc__ += apidoc(solara.SliderDate.f)  # type: ignore
