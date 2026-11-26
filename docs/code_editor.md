# CodeEditor widget

`solara.widgets.CodeEditor` provides a lightweight CodeMirror 6 editor for embedded code entry.

```python
import solara
from solara.widgets import CodeEditor

source = solara.reactive("print('hello world')\n")


@solara.component
def Page():
    CodeEditor(
        value=source.value,
        on_value=lambda value: source.set(value),
        language="python",
        height="260px",
    )
    solara.Pre(format(source.value))


Page()
```

## Options

- `value`: initial and controlled editor content
- `on_value`: callback fired after edits
- `language`: `python`, `javascript`, `json`, `markdown`, or `sql`
- `theme`: reserved for future theme wiring
- `height`: editor height
- `read_only`: disable editing
- `line_numbers`: toggle line numbers
- `tab_size`: indentation width
