import ast
import dataclasses
import operator
from typing import Any, Optional

import solara
import solara.util
from solara.alias import rv

DEBUG = False
operator_map = {
    "x": operator.mul,
    "/": operator.truediv,
    "+": operator.add,
    "-": operator.sub,
}


github_url = solara.util.github_url(__file__)


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
        print("reducer", state, action_type, payload)  # noqa
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
        print("invalid action", action)  # noqa
        return state


@solara.component
def Calculator():
    state, dispatch = solara.use_reducer(calculator_reducer, initial_state)
    if DEBUG:
        print("->", state)  # noqa
    with rv.Card(elevation=10, class_="ma-4") as main:
        with rv.CardTitle(children=["Calculator"]):
            pass
        with rv.CardSubtitle(children=["With ipyvuetify and ipywidgets-react"]):
            pass
        with rv.CardText():
            with solara.VBox(grow=False):
                # with rv.Container(style_="padding: 10px"):
                rv.Label(children=[state.error or state.output or "0"])
                class_ = "pa-0 ma-1"

                with solara.HBox(grow=False):
                    if state.input:
                        rv.BtnWithClick(children="C", on_click=lambda: dispatch(("clear", None)), dark=True, class_=class_)
                    else:
                        rv.BtnWithClick(children="AC", on_click=lambda: dispatch(("reset", None)), dark=True, class_=class_)
                    rv.BtnWithClick(children="+/-", on_click=lambda: dispatch(("negate", None)), dark=True, class_=class_)
                    rv.BtnWithClick(children="%", on_click=lambda: dispatch(("percent", None)), dark=True, class_=class_)
                    rv.BtnWithClick(children="/", color="primary", on_click=lambda: dispatch(("operator", operator_map["/"])), class_=class_)

                column_op = ["x", "-", "+"]
                for i in range(3):
                    with solara.HBox(grow=False):
                        for j in range(3):
                            digit = str(j + (2 - i) * 3 + 1)
                            rv.BtnWithClick(children=digit, on_click=lambda digit=digit: dispatch(("digit", digit)), class_=class_)
                        op_symbol = column_op[i]
                        op = operator_map[op_symbol]
                        rv.BtnWithClick(children=op_symbol, color="primary", on_click=lambda op=op: dispatch(("operator", op)), class_=class_)
                with solara.HBox(grow=False):
                    # rv.Btn(children='gap', style_="visibility: hidden")
                    def boom():
                        print("boom")  # noqa
                        raise ValueError("lala")

                    rv.BtnWithClick(children="?", on_click=boom, class_=class_)

                    rv.BtnWithClick(children="0", on_click=lambda: dispatch(("digit", "0")), class_=class_)
                    rv.BtnWithClick(children=".", on_click=lambda: dispatch(("digit", ".")), class_=class_)

                    rv.BtnWithClick(children="=", color="primary", on_click=lambda: dispatch(("calculate", None)), class_=class_)

    return main


Page = Calculator
