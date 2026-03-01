"""# Todo application

Demonstrates the use of reactive variables in an externally defined state class.

```python
import solara

class TodoItem:
    def __init__(self, text='', done=False):
        self.text = solara.reactive(text)
        self.done = solara.reactive(done)

todo_item = TodoItem("Buy milk", False)

todo_items = solara.reactive([TodoItem("Buy milk", False),
                              TodoItem("Buy whole milk", False)])
```
"""

from typing import Callable

import reacton.ipyvuetify as v

import solara


class TodoItem:
    def __init__(self, text='', done=False):
        self.text = solara.reactive(text)
        self.done = solara.reactive(done)


@solara.component
def TodoEdit(todo_item: TodoItem, on_delete: Callable[[], None], on_close: Callable[[], None]):
    """Takes a reactive todo item and allows editing it. Will not modify the original item until 'save' is clicked."""
    copy = TodoItem(todo_item.text, todo_item.done)

    def save():
        todo_item.text.value = copy.text.value
        on_close()

    with solara.Card("Edit", margin=0):
        solara.InputText(label="", value=copy.text)
        with solara.CardActions():
            v.Spacer()
            solara.Button("Save", icon_name="mdi-content-save", on_click=save, outlined=True, text=True)
            solara.Button("Close", icon_name="mdi-window-close", on_click=on_close, outlined=True, text=True)
            solara.Button("Delete", icon_name="mdi-delete", on_click=on_delete, outlined=True, text=True)


@solara.component
def TodoListItem(todo_item: TodoItem, on_delete: Callable[[TodoItem], None]):
    """Displays a single todo item, modifications are done 'in place'.

    For demonstration purposes, we allow editing the item in a dialog as well.
    This will not modify the original item until 'save' is clicked.
    """
    edit, set_edit = solara.use_state(False)
    with v.ListItem():
        solara.Button(icon_name="mdi-delete", icon=True, on_click=lambda: on_delete(todo_item))
        solara.Checkbox(value=todo_item.done)  # , color="success")
        solara.InputText(label="", value=todo_item.text)
        solara.Button(icon_name="mdi-pencil", icon=True, on_click=lambda: set_edit(True))
        with v.Dialog(v_model=edit, persistent=True, max_width="500px", on_v_model=set_edit):
            if edit:  # 'reset' the component state on open/close

                def on_delete_in_edit():
                    on_delete(todo_item)
                    set_edit(False)

                TodoEdit(todo_item, on_delete=on_delete_in_edit, on_close=lambda: set_edit(False))


@solara.component
def TodoNew(on_new: Callable[[TodoItem], None]):
    """Component that managed entering new todo items"""
    new_text, set_new_text = solara.use_state("")
    text_field = v.TextField(v_model=new_text, on_v_model=set_new_text, label="Enter a new todo item")

    def create_new_item(*ignore_args):
        if not new_text:
            return
        new_item = TodoItem(text=new_text, done=False)
        on_new(new_item)
        # reset text
        set_new_text("")

    v.use_event(text_field, "keydown.enter", create_new_item)
    return text_field


initial_items = [
    TodoItem("Learn Solara", done=True),
    TodoItem("Write cool apps", done=False),
    TodoItem("Relax", done=False),
]


# We store our reactive state, and our logic in a class for organization
# purposes, but this is not required.
# Note that all the above components do not refer to this class, but only
# to do the Todo items.
# This means all above components are reusable, and can be used in other
# places, while the components below use 'application'/'global' state.
# They are not suited for reuse.


class State:
    def __init__(self, initial_items):
        self.todos = solara.reactive(initial_items)

    def on_new(self, item: TodoItem):
        self.todos.value = [item] + self.todos.value

    def on_delete(self, item: TodoItem):
        new_items = list(self.todos.value)
        new_items.remove(item)
        self.todos.value = new_items


@solara.component
def TodoStatus(items):
    """Status of our todo list"""
    count = len(items)
    items_done = [item for item in items if item.done.value]
    count_done = len(items_done)

    if count != count_done:
        with solara.Row():
            percent = count_done / count * 100
            solara.ProgressLinear(value=percent)
        with solara.Row():
            solara.Text(f"Remaining: {count - count_done}")
            solara.Text(f"Completed: {count_done}")
    else:
        solara.Success("All done, awesome!", dense=True)


state = State(initial_items)


@solara.component
def Page():
    with solara.Card("Todo list", style="min-width: 500px"):
        TodoNew(on_new=state.on_new)
        if state.todos.value:
            TodoStatus(state.todos.value)
            for item in state.todos.value:
                TodoListItem(item, on_delete=state.on_delete)
        else:
            solara.Info("No todo items, enter some text above, and hit enter")