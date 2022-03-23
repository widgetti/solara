from ..widgets import DataTable as DataTableWidget
import solara as sol
import solara.hooks.dataframe
import react_ipywidgets as react


import vaex

df = vaex.datasets.titanic()


def test_render():
    @react.component
    def Test():
        return DataTable(df)

    widget, rc = react.render_fixed(Test(), handle_error=False)
    assert isinstance(widget, DataTableWidget)
    assert len(widget.items) == 20


def format_default(df, column, row_index, value):
    return str(value)


@react.component
def DataTable(df, page=0, items_per_page=20, format=None):
    total_length = len(df)
    options = {"descending": False, "page": page + 1, "itemsPerPage": items_per_page, "sortBy": [], "totalItems": total_length}
    options, set_options = react.use_state(options, key="options")
    print(options)
    format = format or format_default
    # frontend does 1 base, we use 0 based
    page = options["page"] - 1
    items_per_page = options["itemsPerPage"]
    i1 = page * items_per_page
    i2 = min(total_length, (page + 1) * items_per_page)

    columns = sol.hooks.dataframe.use_df_column_names(df)

    items = []
    column_data = {}
    dfs = df[i1:i2]
    column_data = dfs.evaluate(columns)
    for i in range(i2 - i1):
        item = {"__row__": i + i1}  # special key for the row number
        for column_index, column in enumerate(columns):
            item[column] = format(dfs, column, i + i1, column_data[column_index][i])
        items.append(item)

    headers = [{"text": name, "value": name, "sortable": False} for name in columns]
    actions = [
        dict(icon="mdi-filter", name="filter"),
        dict(icon="mdi-sort", name="sort"),
    ]

    return DataTableWidget.element(
        total_length=total_length,
        items=items,
        headers=headers,
        headers_selections=[],
        options=options,
        items_per_page=items_per_page,
        selections=[],
        selection_colors=[],
        selection_enabled=False,
        highlighted=None,
        scrollable=False,
        on_options=set_options,
        actions=actions,
    )
