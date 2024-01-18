# Long running code

Solara can run long running code in tasks to have a responsive UI while code runs in the background.
For IO bounds code, we often use async code, which runs in the same thread as your UI.
For CPU intensive, or blocking code, we want to use threads.

## Async task running on an event

```python
import asyncio
import solara
from solara.lab import task

@task
async def fetch_data():
    await asyncio.sleep(2)
    return "The answer is 42"


@solara.component
def Page():
    solara.Button("Fetch data", on_click=fetch_data)
    solara.ProgressLinear(fetch_data.state == solara.ResultState.RUNNING)
    if fetch_data.state == solara.ResultState.FINISHED:
        solara.Text(fetch_data.value)
```


## Threaded task running on an event

```python
import time
import solara
from solara.lab import task

@task
def fetch_data():
    time.sleep(2)
    return "The answer is 42"


@solara.component
def Page():
    print(fetch_data.state)
    solara.Button("Fetch data", on_click=fetch_data)
    solara.ProgressLinear(fetch_data.state == solara.ResultState.RUNNING)
    if fetch_data.state == solara.ResultState.FINISHED:
        solara.Text(fetch_data.value)
```



## Threaded task running when data changes

A common situation in UI's is the need to run and re-run a long running
function when data changes. An example of that is a UI elements like a
[Select](/api/select) which triggers fetching of data from a server.
In this case, the [`use_task`](/api/use_task) hook can be used (with call=True).


```solara
import time
import solara
from solara.lab import task, use_task
import requests


countries = ['Aruba', 'the Netherlands', 'USA', 'China']
country = solara.reactive('Aruba')

@solara.component
def Page():
    def get_country_data():
        return requests.get(f"https://restcountries.com/v3.1/name/{country.value}").json()[0]

    result = use_task(get_country_data, dependencies=[country.value])

    solara.Select("Choose country", value=country, values=countries)
    solara.ProgressLinear(result.state == solara.ResultState.RUNNING)

    if result.state == solara.ResultState.FINISHED:
        languages = result.value["languages"]
        solara.Markdown(f"""
            # Languages in {country.value}

            <pre>
            {repr(languages)}
            </pre>
            """)
    elif result.state == solara.ResultState.ERROR:
        solara.Error(f"Error occurred: {result.error}")
```
