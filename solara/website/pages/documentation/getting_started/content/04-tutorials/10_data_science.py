from pathlib import Path

import solara
import solara.components.applayout
from solara.website.components.notebook import Notebook

HERE = Path(__file__).parent


@solara.component
def Page():
    # only execute once, other
    Notebook(HERE / "_data_science.ipynb")
