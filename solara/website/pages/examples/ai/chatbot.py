"""
    # Chatbot

    A way to create a chatbot using OpenAI's GPT-4 API, utilizing their new API, and the streaming feature.
"""


import os
from typing import Dict, List, Union

from openai import OpenAI

import solara

if os.getenv("OPENAI_API_KEY") is None and "OPENAI_API_KEY" not in os.environ:
    openai = None
else:
    openai = OpenAI()
    openai.api_key = os.getenv("OPENAI_API_KEY")  # type: ignore

messages: solara.Reactive[List[Dict[str, Union[str, bool]]]] = solara.reactive([])


@solara.component
def Page():
    user_message_count = solara.use_reactive(0)

    def send(message):
        messages.set(
            [
                *messages.value,
                {"user": True, "message": message},
            ]
        )
        user_message_count.value += 1

    def call_openai():
        if user_message_count.value == 0:
            return
        if openai is None:
            messages.set(
                [
                    *messages.value,
                    {
                        "user": False,
                        "message": "No OpenAI API key found. Please set your OpenAI API key in the environment variable `OPENAI_API_KEY`.",
                    },
                ]
            )
            return
        response = openai.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "user", "content": messages.value[-1]["message"]},  # type: ignore
            ],
            stream=True,
        )
        messages.set([*messages.value, {"user": False, "message": ""}])
        while True:
            for chunk in response:
                if chunk.choices[0].finish_reason == "stop":  # type: ignore
                    return
                messages.set(
                    [
                        *messages.value[:-1],
                        {
                            "user": False,
                            "message": messages.value[-1]["message"] + chunk.choices[0].delta.content,  # type: ignore
                        },
                    ]
                )

    result = solara.use_thread(call_openai, dependencies=[user_message_count.value])  # type: ignore

    with solara.Column(
        style={"width": "45vw", "height": "50vh"},
    ):
        with solara.lab.ChatBox():
            for item in messages.value:
                with solara.lab.ChatMessage(
                    user=item["user"],
                    avatar=False,
                    name="Bot" if not item["user"] else "User",
                    color="rgba(0,0,0, 0.06)" if not item["user"] else "#ff991f",
                    avatar_background_color="primary" if not item["user"] else None,
                    border_radius="20px",
                ):
                    solara.Markdown(item["message"])
        if result.state == solara.ResultState.RUNNING:
            solara.Text("I'm thinking...", style={"font-size": "1rem", "padding-left": "20px"})
        solara.lab.ChatInput(send_callback=send, disabled=(result.state == solara.ResultState.RUNNING))
