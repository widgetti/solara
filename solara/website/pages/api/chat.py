"""
# Chat Components

These are the components available in Solara to build chat interfaces.
Although they can be used together to create a pre-built chat interface, inserting custom components is also possible.
For an example of how to use a custom message component, see the bottom of the page.

Also check out the [Chatbot](/examples/ai/chatbot) example.

# ChatBox
"""
import solara
from solara.website.utils import apidoc

from . import NoPage

title = "Chat Components"


__doc__ += apidoc(solara.lab.components.chat.ChatBox.f)  # type: ignore
__doc__ += "# ChatInput"
__doc__ += apidoc(solara.lab.components.chat.ChatInput.f)  # type: ignore
__doc__ += "# ChatMessage"
__doc__ += apidoc(solara.lab.components.chat.ChatMessage.f)  # type: ignore
__doc__ += """## Different Message Styles

The `ChatMessage` component has a few different styles available. These are shown below.

```solara
import solara

@solara.component
def Page():
    with solara.Column():
        solara.lab.ChatMessage(["Default"])
        solara.lab.ChatMessage(["`color`"], color="#ff991f")
        solara.lab.ChatMessage(["`avatar_background_color`"], avatar_background_color="success")
        solara.lab.ChatMessage(["`border_radius='20px'`"], border_radius="20px")
        solara.lab.ChatMessage(["`notch=True`"], notch=True)
```
"""

__doc__ += """
# A Basic Example


```solara
import solara

messages = solara.reactive([])
name = solara.reactive("User")

def send(new_message):
    messages.set([
        *messages.value,
        {"user": True, "name": name.value, "message": new_message,},
    ])

@solara.component
def Page():
    solara.InputText("username", value=name)
    with solara.Column(style={"min-height": "50vh"}):
        with solara.lab.ChatBox():
            for item in messages.value:
                with solara.lab.ChatMessage(
                    user=item["user"],
                    name=item["name"],
                ):
                    solara.Markdown(item["message"])
        solara.lab.ChatInput(send_callback=send)
```

# A Custom Message Component

```solara
import solara

messages = solara.reactive([])

def send(new_message):
    messages.set([
        *messages.value,
        {"name": "User", "message": new_message},
    ])

@solara.component
def CustomMessage(
    message,
    name = "User",
):
    with solara.Column(gap=0):
        with solara.Row():
            solara.Markdown(f"**{name}**: {message}")
        solara.v.Divider(style_="margin: 0;")

@solara.component
def Page():
    with solara.Column(style={"min-height": "50vh"}):
        with solara.lab.ChatBox():
            for item in messages.value:
                CustomMessage(
                    message=item["message"],
                    name=item["name"],
                )
        solara.lab.ChatInput(send_callback=send)
```
"""

Page = NoPage
