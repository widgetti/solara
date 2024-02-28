"""
# Cookies and Headers

## Cookies

Solara provides access to cookies through `solara.lab.cookies`.

```python
cookies: Reactive[Optional[Dict[str, str]]] = reactive(cast(Optional[Dict[str, str]], None))
```

This is a reactive object that can be used to read the cookies transferred with the the initial request sent to the server by the client.
Thus it is possible to access also HTTPOnly cookies. The cookies will be updated whenever the client sends a new request to the server,
i.e. only when the client connects to a kernel.

The cookies are read into a dictionary with the cookie names as keys and the cookie values as values.

## Headers

Solara provides access to headers in the form of `solara.lab.headers`.

```python
headers: Reactive[Optional[Dict[str, List[str]]]] = reactive(cast(Optional[Dict[str, List[str]]], None))
```

`headers` concatenates the values of multiple header fields with the same name into a list of strings. However, it is still possible that multiple
values are present in one field already in the request, in which case one string will contain multiple values. Unfortunately reversing this is
highly non-trivial.

Note that the header field names are all lower-case.

```solara
import solara
from solara.lab import headers


@solara.component
def Page():
    solara.Markdown(f"Your 'user-agent' is: {headers.value['user-agent']}")

```

"""

from . import NoPage

title = "Cookies and Headers"
Page = NoPage
