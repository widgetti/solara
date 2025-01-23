"""
# Chatbot

A way to create a chatbot using OpenAI's GPT-4 API, utilizing their new API, and the streaming feature.
"""

import os
from typing import List, cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from typing_extensions import TypedDict

import solara
import solara.lab


class MessageDict(TypedDict):
    role: str  # "user" or "assistant"
    content: str


messages: solara.Reactive[List[MessageDict]] = solara.reactive([])

try:
    import pycafe

    OPENAI_API_KEY = pycafe.get_secret(
        "OPENAI_API_KEY",
        """We need an OpenAI API key to generate text.

Go to [OpenAI](https://platform.openai.com/account/api-keys) to get one.

Or read [this](https://www.rebelmouse.com/openai-account-set-up) article for
more information.

Or read more [about secrets on PyCafe](/docs/secrets)

""",
    )
except ModuleNotFoundError:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def no_api_key_message():
    messages.value = [
        {
            "role": "assistant",
            "content": "No OpenAI API key found. Please set your OpenAI API key in the environment variable `OPENAI_API_KEY`.",
        },
    ]


@solara.lab.task
async def promt_ai(message: str):
    if openai is None:
        no_api_key_message()
        return

    messages.value = [
        *messages.value,
        {"role": "user", "content": message},
    ]
    # The part below can be replaced with a call to your own
    response = await openai.chat.completions.create(
        model="gpt-4-1106-preview",
        # our MessageDict is compatible with the OpenAI types
        messages=cast(List[ChatCompletionMessageParam], messages.value),
        stream=True,
    )
    # start with an empty reply message, so we render and empty message in the chat
    # while the AI is thinking
    messages.value = [*messages.value, {"role": "assistant", "content": ""}]
    # and update it with the response
    async for chunk in response:
        if chunk.choices[0].finish_reason == "stop":  # type: ignore
            return
        # replace the last message element with the appended content
        delta = chunk.choices[0].delta.content
        assert delta is not None
        updated_message: MessageDict = {
            "role": "assistant",
            "content": messages.value[-1]["content"] + delta,
        }
        # replace the last message element with the appended content
        # which will update the UI
        messages.value = [*messages.value[:-1], updated_message]


@solara.component
def Page():
    with solara.Column(
        style={"width": "100%", "height": "50vh"},
    ):
        with solara.lab.ChatBox():
            for item in messages.value:
                with solara.lab.ChatMessage(
                    user=item["role"] == "user",
                    avatar=False,
                    name="ChatGPT" if item["role"] == "assistant" else "User",
                    color="rgba(0,0,0, 0.06)" if item["role"] == "assistant" else "#ff991f",
                    avatar_background_color="primary" if item["role"] == "assistant" else None,
                    border_radius="20px",
                ):
                    solara.Markdown(item["content"])
        if promt_ai.pending:
            solara.Text("I'm thinking...", style={"font-size": "1rem", "padding-left": "20px"})
            solara.ProgressLinear()
        # if we don't call .key(..) with a unique key, the ChatInput component will be re-created
        # and we'll lose what we typed.
        solara.lab.ChatInput(send_callback=promt_ai, disabled_send=promt_ai.pending, autofocus=True).key("input")
