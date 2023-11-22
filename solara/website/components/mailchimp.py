from pathlib import Path

import solara

HERE = Path(__file__).parent

# html = Path(HERE / "mailchimp.v").read_text()


@solara.component_vue("mailchimp.vue")
def MailChimp(location: str):
    pass
