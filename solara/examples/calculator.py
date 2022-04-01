#!/usr/bin/env python
# coding: utf-8


import ast
import dataclasses
import operator
from typing import Any, Optional

import react_ipywidgets as react
import react_ipywidgets.ipyvuetify as v

DEBUG = False
operator_map = {
    "x": operator.mul,
    "/": operator.truediv,
    "+": operator.add,
    "-": operator.sub,
}


@dataclasses.dataclass(frozen=True)
class CalculatorState:
    input: str = ""
    output: str = ""
    left: float = 0
    right: Optional[float] = None
    operator: Any = operator.add
    error: str = ""


initial_state = CalculatorState()


def calculate(state: CalculatorState):
    result = state.operator(state.left, state.right)
    return dataclasses.replace(state, left=result)


def calculator_reducer(state: CalculatorState, action):
    action_type, payload = action
    if DEBUG:
        print("reducer", state, action_type, payload)
    state = dataclasses.replace(state, error="")

    if action_type == "digit":
        digit = payload
        input = state.input + digit
        return dataclasses.replace(state, input=input, output=input)
    elif action_type == "percent":
        if state.input:
            try:
                value = ast.literal_eval(state.input)
            except Exception as e:
                return dataclasses.replace(state, error=str(e))
            state = dataclasses.replace(state, right=value / 100)
            state = calculate(state)
            output = f"{value / 100:,}"
            return dataclasses.replace(state, output=output, input="")
        else:
            output = f"{state.left / 100:,}"
            return dataclasses.replace(state, left=state.left / 100, output=output)
    elif action_type == "negate":
        if state.input:
            input = state.output
            input = input[1:] if input[0] == "-" else "-" + input
            output = input
            return dataclasses.replace(state, input=input, output=output)
        else:
            output = f"{-state.left:,}"
            return dataclasses.replace(state, left=-state.left, output=output)
    elif action_type == "clear":
        return dataclasses.replace(state, input="", output="")
    elif action_type == "reset":
        return initial_state
    elif action_type == "calculate":
        if state.input:
            try:
                value = ast.literal_eval(state.input)
            except Exception as e:
                return dataclasses.replace(state, error=str(e))
            state = dataclasses.replace(state, right=value)
        state = calculate(state)
        output = f"{state.left:,}"
        state = dataclasses.replace(state, output=output, input="")
        return state
    elif action_type == "operator":
        if state.input:
            state = calculator_reducer(state, ("calculate", None))
            state = dataclasses.replace(state, operator=payload, input="")
        else:
            # e.g. 2+3=*= should give 5,25
            state = dataclasses.replace(state, operator=payload, right=state.left)
        return state
    else:
        print("invalid action", action)
        return state


@react.component
def VBox(**kwargs):
    return v.Html(tag="div", style_="display: flex; flex-direction: row", **kwargs)


@react.component
def HBox(**kwargs):
    return v.Html(tag="div", style_="display: flex; flex-direction: column", **kwargs)


@react.component
def Calculator():
    state, dispatch = react.use_reducer(calculator_reducer, initial_state)
    if DEBUG:
        print("->", state)
    with v.Card(elevation=10, class_="ma-4") as main:
        with v.CardTitle(children=["Calculator"]):
            pass
        with v.CardSubtitle(children=["With ipyvuetify and ipywidgets-react"]):
            pass
        with v.CardText():
            with HBox():
                with v.Container(style_="padding: 10px"):
                    v.Label(children=[state.error or state.output or "0"])
                class_ = "pa-0 ma-1"

                with VBox():
                    if state.input:
                        v.BtnWithClick(children="C", on_click=lambda: dispatch(("clear", None)), dark=True, class_=class_)
                    else:
                        v.BtnWithClick(children="AC", on_click=lambda: dispatch(("reset", None)), dark=True, class_=class_)
                    v.BtnWithClick(children="+/-", on_click=lambda: dispatch(("negate", None)), dark=True, class_=class_)
                    v.BtnWithClick(children="%", on_click=lambda: dispatch(("percent", None)), dark=True, class_=class_)
                    v.BtnWithClick(children="/", color="primary", on_click=lambda: dispatch(("operator", operator_map["/"])), class_=class_)

                column_op = ["x", "-", "+"]
                for i in range(3):
                    with VBox():
                        for j in range(3):
                            digit = str(j + (2 - i) * 3 + 1)
                            v.BtnWithClick(children=digit, on_click=lambda digit=digit: dispatch(("digit", digit)), class_=class_)
                        op_symbol = column_op[i]
                        op = operator_map[op_symbol]
                        v.BtnWithClick(children=op_symbol, color="primary", on_click=lambda op=op: dispatch(("operator", op)), class_=class_)
                with VBox():
                    # v.Btn(children='gap', style_="visibility: hidden")
                    def boom():
                        print("boom")
                        raise ValueError("lala")

                    v.BtnWithClick(children="?", on_click=boom, class_=class_)

                    v.BtnWithClick(children="0", on_click=lambda: dispatch(("digit", "0")), class_=class_)
                    v.BtnWithClick(children=".", on_click=lambda: dispatch(("digit", ".")), class_=class_)

                    v.BtnWithClick(children="=", color="primary", on_click=lambda: dispatch(("calculate", None)), class_=class_)

    return main


app = Calculator()

# import react_ipywidgets.bqplot as bqplot
# import react_ipywidgets as react
# import ipywidgets as widgets

# import numpy as np
# x = np.linspace(-2, 2, 100)

# @react.component_interactive(exponent=1.0, static={'x': x},
#                            color=widgets.ColorPicker(value='red'),
#                            line_width=widgets.FloatSlider(value=3, min=0.1, max=10),
#                            log=True)
# def Plot(exponent, x, color, line_width, log):
#     y = (np.abs(x)+0.1) ** exponent

#     scale_x = bqplot.LinearScale(min=-2, max=2.)
#     if log:
#         scale_y = bqplot.LogScale(min=0.01, max=5.)
#     else:
#         scale_y = bqplot.LinearScale(min=0, max=5.)
#     lines = bqplot.Lines(x=x, y=y, scales={'x': scale_x, 'y': scale_y},
#             stroke_width=line_width, colors=[color], display_legend=True, labels=['Line chart'])
#     x_axis = bqplot.Axis(scale=scale_x)
#     y_axis = bqplot.Axis(scale=scale_y, orientation="vertical")
#     axes = [x_axis, y_axis]
#     return bqplot.Figure(axes=axes, marks=[lines], scale_x=scale_x, scale_y=scale_y)

# app = Plot
# from bqplot import pyplot as plt
# import ipyvuetify as v
# import ipywidgets as widgets
# import numpy as np

# import bqplot
# exponent = 1.2
# x = np.arange(-2, 2, 0.01)
# y = (np.abs(x)+0.1) ** exponent
# log = False
# line_width = 1.
# color = "red"

# scale_x = bqplot.LinearScale(min=-2, max=2.)
# if log:
#     scale_y = bqplot.LogScale(min=0.01, max=5.)
# else:
#     scale_y = bqplot.LinearScale(min=0, max=5.)
# lines = bqplot.Lines(x=x, y=y, scales={'x': scale_x, 'y': scale_y},
#         stroke_width=line_width, colors=[color], display_legend=True, labels=['Line chart'])
# x_axis = bqplot.Axis(scale=scale_x)
# y_axis = bqplot.Axis(scale=scale_y, orientation="vertical")
# axes = [x_axis, y_axis]
# app = bqplot.Figure(axes=axes, marks=[lines], scale_x=scale_x, scale_y=scale_y)


# # generate some fake data
# np.random.seed(0)
# n = 2000
# x = np.linspace(0.0, 10.0, n)
# y = np.cumsum(np.random.randn(n)*2. - 1.)#.astype(int)
# # print("HEY " * 100)
# # print(y)

# # create a bqplot figure
# fig_hist = plt.figure(title='Histogram')
# hist = plt.hist(y, bins=25)

# app = fig_hist
# # slider
# slider = v.Slider(thumb_label='always', class_="px-4", v_model=30)
# widgets.link((slider, 'v_model'), (hist, 'bins'))

# fig_lines = plt.figure( title='Line Chart')
# lines = plt.plot(x, y)

# # even handling
# selector = plt.brush_int_selector()
# def update_range(*ignore):
#     if selector.selected is not None and len(selector.selected) == 2:
#         xmin, xmax = selector.selected
#         mask = (x > xmin) & (x < xmax)
#         hist.sample = y[mask]
# selector.observe(update_range, 'selected')


# # control for linestyle
# line_styles = ['dashed', 'solid', 'dotted']
# widget_line_styles = v.Select(items=line_styles, label='line style', v_model=line_styles[0])
# widgets.link((widget_line_styles, 'v_model'), (lines, 'line_style'));

# display(
#     v.Layout(pa_4=True, _metadata={'mount_id': 'content-nav'}, column=True, children=[slider, widget_line_styles])
# )  # use display to support the default template


# fig_hist.layout.width = 'auto'
# fig_hist.layout.height = 'auto'
# fig_hist.layout.min_height = '300px' # so it still shows nicely in the notebook

# fig_lines.layout.width = 'auto'
# fig_lines.layout.height = 'auto'
# fig_lines.layout.min_height = '300px' # so it still shows nicely in the notebook


# app =  v.Layout(
#                     _metadata={'mount_id': 'content-main'},
#                     row=True, wrap=True, align_center=True, children=[
#                     v.Flex(xs12=True, lg6=True, children=[
#                         fig_hist
#                     ]),
#                     v.Flex(xs12=True, lg6=True, children=[
#                         fig_lines
#                     ]),
#                 ])
# # # display(content_main)  # since we are not in a notebook, for default template
