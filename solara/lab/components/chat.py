import uuid
from typing import Callable, Dict, List, Optional, Union

from typing_extensions import Literal

import solara
from solara.components.input import use_change


@solara.component
def ChatBox(
    children: List[solara.Element] = [],
    style: Optional[Union[str, Dict[str, str]]] = None,
    classes: List[str] = [],
):
    """
    The ChatBox component is a container for ChatMessage components.
    Its primary use is to ensure the proper ordering of messages,
    using `flex-direction: column-reverse` together with `reversed(messages)`.

    # Arguments

    * `children`: A list of child components.
    * `style`: CSS styles to apply to the component. Either a string or a dictionary.
    * `classes`: A list of CSS classes to apply to the component.
    """
    style_flat = solara.util._flatten_style(style)
    if "flex-grow" not in style_flat:
        style_flat += " flex-grow: 1;"
    if "flex-direction" not in style_flat:
        style_flat += " flex-direction: column-reverse;"
    if "overflow-y" not in style_flat:
        style_flat += " overflow-y: auto;"

    classes += ["chat-box"]
    with solara.Column(
        style=style_flat,
        classes=classes,
    ):
        for child in list(reversed(children)):
            solara.display(child)


@solara.component
def ChatInput(
    send_callback: Optional[Callable] = None,
    disabled: bool = False,
    style: Optional[Union[str, Dict[str, str]]] = None,
    classes: List[str] = [],
):
    """
    The ChatInput component renders a text input together with a send button.

    # Arguments

    * `send_callback`: A callback function for when the user presses enter or clicks the send button.
    * `disabled`: Whether the input should be disabled. Useful for disabling sending further messages while a chatbot is replying,
        among other things.
    * `style`: CSS styles to apply to the component. Either a string or a dictionary. These styles are applied to the container component.
    * `classes`: A list of CSS classes to apply to the component. Also applied to the container.
    """
    message, set_message = solara.use_state("")  # type: ignore
    style_flat = solara.util._flatten_style(style)

    if "align-items" not in style_flat:
        style_flat += " align-items: center;"

    with solara.Row(style=style_flat, classes=classes):

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
def ChatMessage(
    children: Union[List[solara.Element], str],
    user: bool = False,
    avatar: Union[solara.Element, str, Literal[False], None] = None,
    name: Optional[str] = None,
    color: Optional[str] = "rgba(0,0,0,.06)",
    avatar_background_color: Optional[str] = None,
    border_radius: Optional[str] = None,
    notch: bool = False,
    style: Optional[Union[str, Dict[str, str]]] = None,
    classes: List[str] = [],
):
    """
    The ChatMessage component renders a message. Messages with `user=True` are rendered on the right side of the screen,
    all others on the left.

    # Arguments

    * `children`: A list of child components.
    * `user`: Whether the message is from the current user or not.
    * `avatar`: An avatar to display next to the message. Can be a string representation of a URL or Material design icon name,
        a solara Element, False to disable avatars altogether, or None to display initials based on `name`.
    * `name`: The name of the user who sent the message.
    * `color`: The background color of the message. Defaults to `rgba(0,0,0,.06)`. Can be any valid CSS color.
    * `avatar_background_color`: The background color of the avatar. Defaults to `color` if left as `None`.
    * `border_radius`: Sets the roundness of the corners of the message. Defaults to `None`,
        which applies the default border radius of a `solara.Column`, i.e. `4px`.
    * `notch`: Whether to display a speech bubble style notch on the side of the message.
    * `style`: CSS styles to apply to the component. Either a string or a dictionary. Applied to the container of the message.
    * `classes`: A list of CSS classes to apply to the component. Applied to the same container.
    """
    style_flat = solara.util._flatten_style(style)

    if "border-radius" not in style_flat:
        style_flat += f" border-radius: {border_radius if border_radius is not None else ''};"
    if f"border-top-{'right' if user else 'left'}-radius" not in style_flat:
        style_flat += f" border-top-{'right' if user else 'left'}-radius: 0;"
    if "padding" not in style_flat:
        style_flat += " padding: .5em 1.5em;"

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
        classes_new = classes + ["chat-message-" + msg_uuid, "right" if user else "left"]
        with solara.Column(
            classes=classes_new,
            gap=0,
            style=style_flat,
        ):
            if name is not None:
                solara.Text(name, style="font-weight: bold;", classes=["message-name", "right" if user else "left"])
            for child in children:
                if isinstance(child, solara.Element):
                    solara.display(child)
                else:
                    solara.Markdown(child)
        # we use the uuid to generate 'scoped' CSS, i.e. css that only applies to the component instance.
        extra_styles = (
            f""".chat-message-{msg_uuid}:before{{
                content: '';
                position: absolute;
                width: 0;
                height: 0;
                border: 6px solid;
                top: 0;
            }}
            .chat-message-{msg_uuid}.left:before{{
                left: -12px;
                border-color: var(--color) var(--color) transparent transparent;
            }}
            .chat-message-{msg_uuid}.right:before{{
                right: -12px;
                border-color: var(--color) transparent transparent var(--color);
            }}"""
            if notch
            else ""
        )
        solara.Style(
            f"""
            .chat-message-{msg_uuid}{{
                --color: {color};
                max-width: 75%;
                position: relative;
            }}
            .chat-message-{msg_uuid}.left{{
                    border-top-left-radius: 0;
                    background-color:var(--color);
                    { "margin-left: 10px !important;" if notch else ""}
            }}
            .chat-message-{msg_uuid}.right{{
                    border-top-right-radius: 0;
                    background-color:var(--color);
                    { "margin-right: 10px !important;" if notch else ""}
            }}
            {extra_styles}
            """
        )
