"""# GPT-4 token encoder and decoder

This example shows how to use a language model tokenizer to encode and decode and how to search for a token

Inspired by the Understanding GPT tokenizers by Simon Willison


## Note

Install pandas and tiktoken with `pip install pandas tiktoken`

"""
import random

import pandas as pd
import tiktoken

import solara
import solara.lab

# Get tokenizer for gpt-4
tokenizer = tiktoken.encoding_for_model("gpt-4")

# Create dataframe mapping token IDs and tokens
MAX_TOKENS = 50257
df = pd.DataFrame()
df["token ID"] = range(MAX_TOKENS)
df["token"] = [tokenizer.decode([i]) for i in range(MAX_TOKENS)]

sentence = solara.reactive("Example text is here")
tokens_ids_to_lookup = solara.reactive("")
tokens_filter = solara.reactive("")


@solara.component
def Token(token: int):
    random.seed(token)
    random_color = "".join([random.choice("0123456789ABCDEF") for k in range(6)])
    with solara.Div(style="display: inline;"):
        with solara.Div(
            style={
                "display": "inline",
                "padding": "6px",
                "border-right": "3px solid white",
                "line-height": "3em",
                "font-family": "courier",
                "background-color": f"#{random_color}",
                "color": "white",
                "position": "relative",
            },
        ):
            solara.Text(
                " " + str(token),
                style={
                    "display": "inline",
                    "position": "absolute",
                    "top": "5.5ch",
                    "line-height": "1em",
                    "left": "-0.5px",
                    "font-size": "0.45em",
                },
            )
            solara.Text(str(tokenizer.decode([token])))


@solara.component
def Page():
    with solara.Column(margin=10):
        solara.Markdown("#GPT-4 token encoder and decoder")
        solara.Markdown("This is an educational tool for understanding how tokenization works.")
        solara.InputText("Enter text to tokenize it:", value=sentence, continuous_update=True)
        tokens = tokenizer.encode(sentence.value)
        with solara.Div(style="display: inline;"):
            for i, token in enumerate(tokens):
                Token(token)
        # create random color dependent on the position
        solara.InputText("Or convert space separated tokens to text:", value=tokens_ids_to_lookup, continuous_update=True)
        token_input = [int(span) for span in tokens_ids_to_lookup.value.split(" ") if span != ""]
        text_output = tokenizer.decode(token_input)
        solara.Markdown(f"{text_output}")
        solara.Markdown("##Search tokens")
        solara.InputText("Search for a token:", value=tokens_filter, continuous_update=True)
        df_subset = df[df["token"].str.startswith(tokens_filter.value)]
        solara.Markdown(f"{df_subset.shape[0]:,} results")
        solara.DataFrame(df_subset, items_per_page=10)
