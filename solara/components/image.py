import typing
from pathlib import Path
from typing import List, Optional, Union

import solara
from solara.alias import rw

if typing.TYPE_CHECKING:
    import numpy as np


@solara.component
def Image(image: Union[str, Path, "np.ndarray"], width: Optional[str] = None, classes: List[str] = []):
    """Displays an image from a URL, Path or numpy data.

    ## Arguments
     * `image`: URL, Path or numpy data.
     * `width`: Width of the image, by default (None) the image is displayed at its original size.
        Other options are: "100%" (to full its parent size), "100px" (to display it at 100 pixels wide),
        or any other CSS width value.
     * `classes`: List of CSS classes to add to the image.
    """
    layout = {}
    if width:
        layout["width"] = width
    classes = ["solara-image"] + classes
    if isinstance(image, (str, Path)):
        path = Path(image)
        if path.exists():
            import ipywidgets

            format = ipywidgets.Image._guess_format("image", str(path))
            value = ipywidgets.Image._load_file_value(str(path))
            return rw.Image(
                value=value,
                format=format,
                _dom_classes=classes,  # type: ignore
                layout=layout,
            )
        elif isinstance(image, str):
            url_data = image.encode("utf8")
            return rw.Image(
                value=url_data,
                format="url",
                _dom_classes=classes,  # type: ignore
                layout=layout,
            )
    elif solara.util.isinstanceof(image, "numpy:ndarray"):
        value = solara.util.numpy_to_image(image, format="png")
        return rw.Image(
            value=value,
            format="image/png",
            _dom_classes=classes,  # type: ignore
            layout=layout,
        )
    raise TypeError(f"Only support URL, path or numpy array, not {image}")
