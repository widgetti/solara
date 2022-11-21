"""# Image
"""

from pathlib import Path

import numpy as np
import PIL.Image

import solara
import solara.website
from solara.website.utils import apidoc


@solara.component
def Page():

    image_path = Path(solara.website.__file__).parent / "public/beach.jpeg"
    image_url = "/static/public/beach.jpeg"
    image_ndarray = np.asarray(PIL.Image.open(image_path))

    with solara.VBox() as main:
        with solara.Card(title="As a path"):
            solara.Image(image_path)

        with solara.Card(title="As a URL"):
            solara.Image(image_url)

        with solara.Card(title="As NumPy array"):
            solara.Image(image_ndarray)

    return main


__doc__ += apidoc(solara.Image.f)  # type: ignore
