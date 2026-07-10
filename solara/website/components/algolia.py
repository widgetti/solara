import solara
from solara.util import IPYVUETIFY_V3


@solara.component_vue("algolia_api_v3.vue" if IPYVUETIFY_V3 else "algolia_api.vue")
def Algolia():
    pass
