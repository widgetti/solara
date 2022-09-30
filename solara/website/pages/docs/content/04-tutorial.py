import linecache
from pathlib import Path
from typing import Any, Dict

import nbformat
import solara

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
            source = cell.source
            cell_path = f"app.ipynb input cell {cell_index}"
            ast = compile(source, cell_path, "exec")
            entry = (
                stat.st_size,
                stat.st_mtime,
                [line + "\n" for line in source.splitlines()],
                cell_path,
            )
            linecache.cache[cell_path] = entry
            exec(ast, scope)
            # every cell gets a snapshot of the scope
            scope_snapshot = {**scope}
            # avoid the buggy setitem of NotebookNode
            # which causes an recursion error
            cell.__dict__["scope_snapshot"] = scope_snapshot
        elif cell.cell_type == "markdown":
            pass
        else:
            raise ValueError(f"Unknown cell type: {cell.cell_type}, supported types are: code, markdown")
    return nb


@solara.component
def Page():
    # only execute once, other
    nb: nbformat.NotebookNode = solara.use_memo(lambda: execute_notebook(HERE / "_solara-tutorial.ipynb"))

    last_page = None
    with solara.VBox() as main:
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
                    page()
                last_page = page
            elif cell.cell_type == "markdown":
                solara.Markdown(cell.source)
            else:
                raise ValueError(f"Unknown cell type: {cell.cell_type}, supported types are: code, markdown")
    return main
