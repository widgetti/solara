import logging

import reacton.ipyvuetify as v
import solara

from solara_enterprise import auth

logging.basicConfig(filename="./log.log", level=logging.INFO, format="[%(threadName)s] - %(name)s - %(asctime)s %(message)s")


@solara.component
def Page():
    from solara_enterprise.auth import user as solara_user

    solara_user.use()
    logging.getLogger("solara.server.fastapi").warning(f" user {solara_user.get()}")

    sentence, set_sentence = solara.use_state("Solara makes our team more productive.")
    word_limit, set_word_limit = solara.use_state(10)
    word_count = len(sentence.split())

    solara.SliderInt("Word limit", value=word_limit, on_value=set_word_limit, min=2, max=20)
    solara.InputText(label="Your sentence", value=sentence, on_value=set_sentence, continuous_update=True)

    with solara.Div():
        if word_count >= int(word_limit):
            solara.Error(f"With {word_count} words, you passed the word limit of {word_limit}.")
        elif word_count >= int(0.8 * word_limit):
            solara.Warning(f"With {word_count} words, you are close to the word limit of {word_limit}.")
        else:
            solara.Success("Great short writing!")
        solara.Div(children=[str(solara_user.get())])
        v.Html(tag="a", attributes={"href": auth.get_logout_url()}, children=["logout"])
