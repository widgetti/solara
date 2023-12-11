# Search

Solara can provide search, if [SSG](/docs/reference/static-site-generation) is enabled. This allows you to add a search box to you website, which performs a full-text search to provide quick access to pages. The solara website itself uses the
search feature as well in the toolbar.

## Using Solara's Search feature.

By running `solara run myapp.pages --ssg --search` solara will fetch all your pages, and build up a search index afterards. This option can also be abled using the environment variable `SOLARA_SEARCH_ENABLED=True`.

You can import as use the Search component as follow:

```
import solara
from solara_enterprise.search.search import Search


@solara.component
def Page():
    with MyToolbar():
        ...
        Search()
```

## Requirements

This feature requires `solara-enterprise`, which can be installed as follows:

```
pip install solara-enterprise
```
