"""# Calculator

This shows how to use `use_reducer` to implement a simple calculator.

Note that the `reducer` implements all the logic of the calculator, and the `Calculator` component is just a thin wrapper around it.



"""

import ast
import dataclasses
import operator
from typing import Any, Optional

import solara

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
    with solara.Card("Calculator", elevation=10, classes=["ma-4"]) as main:
        with solara.VBox(grow=False):
            solara.Text(state.error or state.output or "0")
            class_ = "pa-0 ma-1"

            with solara.HBox(grow=False):
                if state.input:
                    solara.Button("C", on_click=lambda: dispatch(("clear", None)), dark=True, class_=class_)
                else:
                    solara.Button("AC", on_click=lambda: dispatch(("reset", None)), dark=True, class_=class_)
                solara.Button("+/-", on_click=lambda: dispatch(("negate", None)), dark=True, class_=class_)
                solara.Button("%", on_click=lambda: dispatch(("percent", None)), dark=True, class_=class_)
                solara.Button("/", color="primary", on_click=lambda: dispatch(("operator", operator_map["/"])), class_=class_)

            column_op = ["x", "-", "+"]
            for i in range(3):
                with solara.HBox(grow=False):
                    for j in range(3):
                        digit = str(j + (2 - i) * 3 + 1)

                        def on_click(digit=digit):
                            dispatch(("digit", digit))

                        solara.Button(digit, on_click=on_click, class_=class_)
                    op_symbol = column_op[i]
                    op = operator_map[op_symbol]

                    def on_click_op(op=op):
                        dispatch(("operator", op))

                    solara.Button(op_symbol, color="primary", on_click=on_click_op, class_=class_)
            with solara.HBox(grow=False):

                def boom():
                    print("boom")  # noqa
                    raise ValueError("lala")

                solara.Button("?", on_click=boom, class_=class_)

                solara.Button("0", on_click=lambda: dispatch(("digit", "0")), class_=class_)
                solara.Button(".", on_click=lambda: dispatch(("digit", ".")), class_=class_)

                solara.Button("=", color="primary", on_click=lambda: dispatch(("calculate", None)), class_=class_)

    return main


Page = Calculator
