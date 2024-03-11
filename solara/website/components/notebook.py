import ast
import linecache
from pathlib import Path
from typing import Any, Dict

import IPython
import nbformat

import solara
import solara.components.applayout
import solara.toestand
from solara.components.markdown import ExceptionGuard

HERE = Path(__file__).parent


def execute_notebook(path: Path):
    nb: nbformat.NotebookNode = nbformat.read(path, 4)
    stat = path.stat()
    scope: Dict[str, Any] = {}
    for cell_index, cell in enumerate(nb.cells):
        cell_index += 1  # used 1 based
        cell.scope_snapshot = {}
        if cell.cell_type == "code":
            if cell.source.startswith("## solara: skip"):
                continue

            def execute(cell=cell):
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
                with solara.Column():
                    if code.body:
                        last_statement = code.body[-1]
                        if isinstance(last_statement, ast.Expr):
                            code.body.pop()
                            last = ast.Expression(last_statement.value)
                            exec(compile(code, "<string>", mode="exec"), scope)
                            value = eval(compile(last, "<string>", mode="eval"), scope)
                        else:
                            exec(compile(code, "<string>", mode="exec"), scope)
                    import matplotlib_inline.backend_inline

                    matplotlib_inline.backend_inline.flush_figures()
                scope_snapshot = {**scope}
                cell.__dict__["scope_snapshot"] = scope_snapshot
                return value

            # every cell gets a snapshot of the scope
            # avoid the buggy setitem of NotebookNode
            # which causes an recursion error
            yield cell_index, cell, execute
        elif cell.cell_type == "markdown":
            # last_expressions.append(None)
            yield cell_index, cell, lambda: None
        else:
            raise ValueError(f"Unknown cell type: {cell.cell_type}, supported types are: code, markdown")


@solara.component
def NotebookExecute(notebook_path: Path, show_last_expressions=False, auto_show_page=False):
    import IPython.core.pylabtools as pylabtools

    shell = IPython.get_ipython().kernel.shell

    # TODO: there is a change the cleanup will not be called
    pylabtools.select_figure_formats(shell, ["png"])

    def cleanup():
        def _cleanup():
            from matplotlib.figure import Figure

            png_formatter = shell.display_formatter.formatters["image/png"]
            png_formatter.pop(Figure)

        return _cleanup

    solara.use_effect(cleanup, [])
    values = list(solara.use_memo(lambda: execute_notebook(notebook_path)))

    last_page = None

    solara.components.applayout.should_use_embed.provide(True)
    with solara.Column(style={"max-width": "100%"}) as main:

        for cell_index, cell, executor in values:
            cell_index += 1  # used 1 based
            if cell.cell_type == "code":
                if cell.source.startswith("## solara: skip"):
                    continue
                solara.Markdown(
                    f"""
```python
{cell.source}
```"""
                )
                # we execute here, such that any side effect (display, etc)
                # will be done under the context of the Column
                with ExceptionGuard():
                    with solara.AppLayout(navigation=False, toolbar_dark=True):
                        # we don't want to listen to reactive variables
                        copy = set(solara.toestand.thread_local.reactive_used or [])
                        try:
                            last_expression = executor()
                        finally:
                            solara.toestand.thread_local.reactive_used = copy
                    scope = cell.scope_snapshot
                    page = scope.get("Page")
                    if auto_show_page and page != last_page and page is not None:
                        page()
                    else:
                        if show_last_expressions:
                            if last_expression is not None:
                                solara.display(last_expression)
                last_page = page
            elif cell.cell_type == "markdown":
                solara.Markdown(cell.source)
            else:
                raise ValueError(f"Unknown cell type: {cell.cell_type}, supported types are: code, markdown")
    return main


@solara.component
def Notebook(notebook_path: Path, show_last_expressions=False, auto_show_page=False, execute=True, outputs={}):
    if execute:
        return NotebookExecute(notebook_path, show_last_expressions, auto_show_page)
    else:
        with solara.Column(style={"max-width": "100%"}) as main:
            nb: nbformat.NotebookNode = nbformat.read(notebook_path, 4)
            for cell_index, cell in enumerate(nb.cells):
                cell_index += 1
                if cell.cell_type == "code":
                    if cell.source.startswith("## solara: skip"):
                        continue
                    solara.Markdown(
                        f"""
```python
{cell.source}
```"""
                    )
                    if cell.outputs:
                        for output in cell.outputs:
                            if output.output_type == "display_data":
                                solara.display(output.data, raw=True)
                            elif output.output_type == "execute_result":
                                if "text/html" in output.data:
                                    solara.display(output.data, raw=True)
                    else:
                        cell_id = str(cell.id)
                        output = outputs.get(cell_id) or outputs.get(cell_index)
                        if output is None:
                            if cell_id in outputs or cell_index in outputs:
                                pass  # explicit None
                            else:
                                solara.display(f"Output missing for cell: {cell_index} id {cell_id}")
                        else:
                            solara.display(output)

                elif cell.cell_type == "markdown":
                    solara.Markdown(cell.source)
                else:
                    raise ValueError(f"Unknown cell type: {cell.cell_type}, supported types are: code, markdown")
        return main
