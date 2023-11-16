import uuid
from typing import Callable, List, Literal, Optional, Union

import solara
from solara.components.input import use_change


@solara.component
def ChatMessage(
    children: Union[List[solara.Element], str],
    user: bool = False,
    avatar: Union[solara.Element, str, Literal[False], None] = None,
    name: Optional[str] = None,
    color: Optional[str] = "rgba(0,0,0,.06)",
    avatar_background_color: Optional[str] = None,
    border_radius: Optional[str] = None,
    notch: bool = False,
):
    msg_uuid = solara.use_memo(lambda: str(uuid.uuid4()), dependencies=[])
    with solara.Row(
        justify="end" if user else "start",
        style={"flex-direction": "row-reverse" if user else "row", "padding": "5px"},
    ):
        if avatar is not False:
            with solara.v.Avatar(color=avatar_background_color if avatar_background_color is not None else color):
                if avatar is None and name is not None:
                    initials = "".join([word[:1] for word in name.split(" ")])
                    solara.HTML(tag="span", unsafe_innerHTML=initials, classes=["headline"])
                elif isinstance(avatar, solara.Element):
                    solara.display(avatar)
                elif isinstance(avatar, str) and avatar.startswith("mdi-"):
                    solara.v.Icon(children=[avatar])
                else:
                    solara.HTML(tag="img", attributes={"src": avatar, "width": "100%"})
        with solara.Column(
            classes=["chat-message-" + msg_uuid, "right" if user else "left"],
            gap=0,
            style="border-radius: "
            + (border_radius if border_radius is not None else "")
            + "; border-top-"
            + ("right" if user else "left")
            + "-radius: 0; padding: .5em 1.5em;",
        ):
            if name is not None:
                solara.Text(name, style="font-weight: bold;", classes=["message-name", "right" if user else "left"])
            solara.display(*children)
        solara.Style(
            ".chat-message-"
            + msg_uuid
            + "{"
            + "--color:"
            + color
            + ";"
            + """
                    max-width: 75%;
                    position: relative;
                }"""
            + ".chat-message-"
            + msg_uuid
            + """.left{
                    border-top-left-radius: 0;
                    background-color:var(--color);
                }"""
            + ".chat-message-"
            + msg_uuid
            + """.right{
                    border-top-right-radius: 0;
                    background-color:var(--color);
                }"""
        )
        if notch:
            solara.Style(
                ".chat-message-"
                + msg_uuid
                + """.right{
                    margin-right: 10px !important;
                }
                .chat-message-"""
                + msg_uuid
                + """.left{
                    margin-left: 10px !important;
                }
                .chat-message-"""
                + msg_uuid
                + """:before{
                        content: '';
                        position: absolute;
                        width: 0;
                        height: 0;
                        border: 6px solid;
                        top: 0;
                    }"""
                + ".chat-message-"
                + msg_uuid
                + """.left:before{
                        left: -12px;
                        border-color: var(--color) var(--color) transparent transparent;
                    }"""
                + ".chat-message-"
                + msg_uuid
                + """.right:before{
                        right: -12px;
                        border-color: var(--color) transparent transparent var(--color);
                    }
                """
            )


@solara.component
def ChatBox(children: List[solara.Element] = []):
    with solara.Column(style={"flex-grow": "1", "flex-direction": "column-reverse", "overflow-y": "auto"}, classes=["chat-box"]):
        for child in list(reversed(children)):
            solara.display(child)


@solara.component
def ChatInfo(children: List[solara.Element] = []):
    with solara.Row(style={"min-height": "1em"}):
        if children != []:
            solara.display(*children)


@solara.component
def ChatInput(
    send_callback: Optional[Callable] = None,
    disabled: bool = False,
):
    message, set_message = solara.use_state("")  # type: ignore

    with solara.Row(style={"align-items": "center"}):

        def send(*ignore_args):
            if message != "" and send_callback is not None:
                send_callback(message)
                set_message("")

        message_input = solara.v.TextField(
            label="Type a message...",
            v_model=message,
            on_v_model=set_message,
            rounded=True,
            filled=True,
            hide_details=True,
            style_="flex-grow: 1;",
            disabled=disabled,
        )

        use_change(message_input, send, update_events=["keyup.enter"])

        button = solara.v.Btn(color="primary", icon=True, children=[solara.v.Icon(children=["mdi-send"])], disabled=message == "")

        use_change(button, send, update_events=["click"])


@solara.component
def ChatInterface(
    children: List[solara.Element] = [],
):
    children_info = []
    children_input = []
    children_chatbox = []
    children_others = []

    for child in children:
        if isinstance(child, solara.Element) and child.component == ChatInfo:
            children_info.append(child)
        elif isinstance(child, solara.Element) and child.component == ChatInput:
            children_input.append(child)
        elif isinstance(child, solara.Element) and child.component == ChatBox:
            children_chatbox.append(child)
        else:
            children_others.append(child)

    with solara.Column(style={"height": "100%"}):
        solara.display(*children_chatbox)
        solara.display(*children_info)
        solara.display(*children_input)
        solara.display(*children_others)
