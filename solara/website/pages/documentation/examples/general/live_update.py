from typing import cast, Optional
import httpx
import asyncio
import solara
import solara.lab


@solara.component
def Page():
    btc = solara.use_reactive(cast(Optional[float], None))

    async def fetch_btc_price():
        while True:
            await asyncio.sleep(1)
            async with httpx.AsyncClient() as client:
                url = "https://api.binance.com/api/v1/ticker/price?symbol=BTCUSDT"
                response = await client.get(url)
                btc.value = float(response.json()["price"])
                print("btc.value", btc.value)

    fetch_result = solara.lab.use_task(fetch_btc_price, dependencies=[])
    # the task keeps running, so is always in the pending mode, so we combine it with the btc value being None
    if fetch_result.pending and btc.value is None:
        solara.Text("Fetching BTC price...")
    else:
        if fetch_result.error:
            solara.Error(f"Error fetching BTC price: {fetch_result.exception}")
        else:
            solara.Text(f"BTC price: ${btc.value}")


Page()
