from typing import Dict, List

import ipyvue
import traitlets

import solara


class SqlCodeWidget(ipyvue.VueTemplate):
    template_file = (__file__, "sql_code.vue")

    label = traitlets.Unicode("").tag(sync=True)
    query = traitlets.Unicode(allow_none=True, default_value=None).tag(sync=True)
    tables = traitlets.Dict(allow_none=True, default_value=None).tag(sync=True)
    height = traitlets.Unicode("180px").tag(sync=True)


@solara.component
def SqlCode(label="Query", query: str = None, tables: Dict[str, List[str]] = None, on_query=None, height="180px"):
    """SQL textfield input with auto complete and SQL syntax highlighting.

    To get auto complete for the column names, prefix it with the table name, i.e. "titanic.sur ctrl+space"

    ## Arguments

     * `label`: Label for the textfield.
     * `query`: SQL query.
     * `tables`: Dictionary with table names as keys and list of column names as values (used for auto complete).
     * `on_query`: Callback function that is called when the query is changed
     * `height`: Height of the textfield

    """
    return SqlCodeWidget.element(label=label, query=query, tables=tables, on_query=on_query, height=height)
