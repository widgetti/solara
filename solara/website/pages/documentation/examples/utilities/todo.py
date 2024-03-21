"""# Todo application

Demonstrates the use of reactive variables in combinations with dataclasses.

With solara we can get a type safe view onto a field in a dataclass, pydantic model, or
attr object.

This is using the experimental `solara.lab.Ref` class, which is not yet part of the
official API.


```python
import dataclasses
import solara
from solara.lab import Ref

@dataclasses.dataclass(frozen=True)
class TodoItem:
    text: str
    done: bool

todo_item = solara.reactive(TodoItem("Buy milk", False))

# now text is a reactive variable that is always in sync with todo_item.text
text = Ref(todo_item.fields.text)


# we can now modify the reactive text variable
# and see its value reflect in the todo_item
text.value = "Buy skimmed milk"
assert todo_item.value.text == "Buy skimmed milk"

# Or, the other way around
todo_item.value = TodoItem("Buy whole milk", False)
assert text.value == "Buy whole milk"
```

Apart from dataclasses, pydantic models etc, we also supports dictionaries and lists.

```python
todo_items = solara.reactive([TodoItem("Buy milk", False), TodoItem("Buy eggs", False)])
todo_item_eggs = Ref(todo_items.fields[1])
todo_item_eggs.value = TodoItem("Buy eggs", True)
assert todo_items.value[1].done == True

# However, if a list becomes shorter, and the valid index is now out of range, the
# reactive variables will act as if it is "not connected", and will not trigger
# updates anymore. Accessing the value will raise an IndexError.

todo_items.value = [TodoItem("Buy milk", False)]
# anyone listening to todo_item_eggs will *not* be notified.
try:
    value = todo_item_eggs.value
except IndexError:
    print("this is expected")
else:
    raise AssertionError("Expected an IndexError")
```

"""
import dataclasses
from typing import Callable

import reacton.ipyvuetify as v

import solara
from solara.lab.toestand import Ref


# our model for a todo item, immutable/frozen avoids common bugs
@dataclasses.dataclass(frozen=True)
class TodoItem:
    text: str
    done: bool


@solara.component
def TodoEdit(todo_item: solara.Reactive[TodoItem], on_delete: Callable[[], None], on_close: Callable[[], None]):
    """Takes a reactive todo item and allows editing it. Will not modify the original item until 'save' is clicked."""
    copy = solara.use_reactive(todo_item.value)

    def save():
        todo_item.value = copy.value
        on_close()

    with solara.Card("Edit", margin=0):
        solara.InputText(label="", value=Ref(copy.fields.text))
        with solara.CardActions():
            v.Spacer()
            solara.Button("Save", icon_name="mdi-content-save", on_click=save, outlined=True, text=True)
            solara.Button("Close", icon_name="mdi-window-close", on_click=on_close, outlined=True, text=True)
            solara.Button("Delete", icon_name="mdi-delete", on_click=on_delete, outlined=True, text=True)


@solara.component
def TodoListItem(todo_item: solara.Reactive[TodoItem], on_delete: Callable[[TodoItem], None]):
    """Displays a single todo item, modifications are done 'in place'.

    For demonstration purposes, we allow editing the item in a dialog as well.
    This will not modify the original item until 'save' is clicked.
    """
    edit, set_edit = solara.use_state(False)
    with v.ListItem():
        solara.Button(icon_name="mdi-delete", icon=True, on_click=lambda: on_delete(todo_item.value))
        solara.Checkbox(value=Ref(todo_item.fields.done))  # , color="success")
        solara.InputText(label="", value=Ref(todo_item.fields.text))
        solara.Button(icon_name="mdi-pencil", icon=True, on_click=lambda: set_edit(True))
        with v.Dialog(v_model=edit, persistent=True, max_width="500px", on_v_model=set_edit):
            if edit:  # 'reset' the component state on open/close

                def on_delete_in_edit():
                    on_delete(todo_item.value)
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


# We store out reactive state, and our logic in a class for organization
# purposes, but this is not required.
# Note that all the above components do not refer to this class, but only
# to do the Todo items.
# This means all above components are reusable, and can be used in other
# places, while the components below use 'application'/'global' state.
# They are not suited for reuse.


class State:
    todos = solara.reactive(initial_items)

    @staticmethod
    def on_new(item: TodoItem):
        State.todos.value = [item] + State.todos.value

    @staticmethod
    def on_delete(item: TodoItem):
        new_items = list(State.todos.value)
        new_items.remove(item)
        State.todos.value = new_items


@solara.component
def TodoStatus():
    """Status of our todo list"""
    items = State.todos.value
    count = len(items)
    items_done = [item for item in items if item.done]
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


@solara.component
def Page():
    with solara.Card("Todo list", style="min-width: 500px"):
        TodoNew(on_new=State.on_new)
        if State.todos.value:
            TodoStatus()
            for index, item in enumerate(State.todos.value):
                todo_item = Ref(State.todos.fields[index])
                TodoListItem(todo_item, on_delete=State.on_delete)
        else:
            solara.Info("No todo items, enter some text above, and hit enter")
