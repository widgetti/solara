import ast
import linecache
from pathlib import Path
from typing import Any, Dict

import nbformat

import solara
import solara.components.applayout
from solara.components.markdown import ExceptionGuard

if solara._using_solara_server():
    from matplotlib import pyplot as plt

    plt.switch_backend("agg")

HERE = Path(__file__).parent


def execute_notebook(path: Path):
    nb: nbformat.NotebookNode = nbformat.read(path, 4)
    stat = path.stat()
    last_expressions = []
    scope: Dict[str, Any] = {}
    for cell_index, cell in enumerate(nb.cells):
        cell_index += 1  # used 1 based
        cell.scope_snapshot = {}
        if cell.cell_type == "code":
            if cell.source.startswith("## solara: skip"):
                continue
            source = cell.source
            cell_path = f"app.ipynb input cell {cell_index}"
            entry = (
                stat.st_size,
                stat.st_mtime,
                [line + "\n" for line in source.splitlines()],
                cell_path,
            )

            linecache.cache[cell_path] = entry
            code = ast.parse(source, cell_path, "exec")
            value = None
            if code.body:
                last_statement = code.body[-1]
                if isinstance(last_statement, ast.Expr):
                    code.body.pop()
                    last = ast.Expression(last_statement.value)
                    exec(compile(code, "<string>", mode="exec"), scope)
                    value = eval(compile(last, "<string>", mode="eval"), scope)
                else:
                    exec(compile(code, "<string>", mode="exec"), scope)

            last_expressions.append(value)
            # every cell gets a snapshot of the scope
            scope_snapshot = {**scope}
            # avoid the buggy setitem of NotebookNode
            # which causes an recursion error
            cell.__dict__["scope_snapshot"] = scope_snapshot
        elif cell.cell_type == "markdown":
            last_expressions.append(None)
        else:
            raise ValueError(f"Unknown cell type: {cell.cell_type}, supported types are: code, markdown")
    return nb, last_expressions


@solara.component
def Notebook(notebook_path: Path, show_last_expressions=False):
    # only execute once, other
    nb: nbformat.NotebookNode
    nb, values = solara.use_memo(lambda: execute_notebook(notebook_path))

    last_page = None

    solara.components.applayout.should_use_embed.provide(True)
    with solara.Column(style={"max-width": "100%"}) as main:
        for cell_index, cell in list(enumerate(nb.cells)):
            cell_index += 1  # used 1 based
            if cell.cell_type == "code":
                if cell.source.startswith("## solara: skip"):
                    continue
                scope = cell.scope_snapshot
                page = scope.get("Page")
                solara.Markdown(
                    f"""
```python
{cell.source}
```"""
                )
                if page != last_page and page is not None:
                    with solara.AppLayout(navigation=False, toolbar_dark=True):
                        with ExceptionGuard():
                            page()
                else:
                    if show_last_expressions:
                        last_expression = values[cell_index - 1]
                        if last_expression is not None:
                            solara.display(last_expression)
                last_page = page
            elif cell.cell_type == "markdown":
                solara.Markdown(cell.source)
            else:
                raise ValueError(f"Unknown cell type: {cell.cell_type}, supported types are: code, markdown")
    return main
