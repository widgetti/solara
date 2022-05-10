import threading
from typing import Callable, TypeVar

import pandas as pd
import pandas_ta as ta  # noqa: F401
import plotly.graph_objects as go
import typing_extensions

from solara.datatypes import Result
from solara.hooks.misc import use_thread
from solara.kitchensink import react, sol, v

P = typing_extensions.ParamSpec("P")
T = TypeVar("T")


def make_use_thread(f: Callable[P, T]):
    def use_result(*args: P.args, **kwargs: P.kwargs) -> Result[T]:
        def in_thread(cancel: threading.Event):
            return f(*args, **kwargs)

        return use_thread(in_thread, dependencies=[args, kwargs])

    return use_result


@make_use_thread
def use_load_df(ticker, period, interval) -> pd.DataFrame:
    @sol.memoize()
    def load(ticker, period, interval):
        e = pd.DataFrame()
        df = e.ta.ticker(ticker, period=period, interval=interval, kind="info", lc_cols=True)
        print(df)
        if df is None:
            raise ValueError("Error loading, nothing returned")
        return df

    return load(ticker, period, interval)


periods = "1d 5d 1mo 3mo 6mo 1y 2y 5y 10y ytd max".split()
intervals = "1m 2m 5m 15m 30m 60m 90m 1h 1d 5d 1wk 1mo 3mo".split()
tickers = ["BTC-USD", "SPY"]


@react.component
def App():
    ticker, set_ticker = react.use_state("SPY")
    period, set_period = react.use_state("1y")
    interval, set_interval = react.use_state("1wk")
    df_result = use_load_df(ticker, period=period, interval=interval)

    with sol.Div() as main:
        v.Select(items=tickers, v_model=ticker, on_v_model=set_ticker, label="Ticker")
        v.Select(items=periods, v_model=period, on_v_model=set_period, label="Period")
        v.Select(items=intervals, v_model=interval, on_v_model=set_interval, label="Interval")
        ema_length = sol.ui_slider(value=8, min=2, max=100, description="Length (EMA)")

        if df_result.error:
            sol.Error(f"Error: {df_result.error}")
            sol.Button("Retry", on_click=df_result.retry)
        else:
            if df_result.value is not None:
                df = df_result.value
                ema = df.ta.ema(length=ema_length)
                fig = go.Figure(
                    data=[
                        go.Ohlc(
                            x=df.index,
                            open=df["open"],
                            high=df["high"],
                            low=df["low"],
                            close=df["close"],
                            name=ticker,
                        ),
                        go.Scatter(x=ema.index, y=ema.values, name=f"{ticker}_EMA_{ema_length}", mode="lines"),
                    ]
                )
                sol.FigurePlotly(fig, dependencies=[])
            else:
                with v.Text(children=["Loading data..."]):
                    v.ProgressCircular(indeterminate=True, class_="solara-progress")

    return main


app = App()
