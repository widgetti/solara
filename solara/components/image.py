import typing
from pathlib import Path
from typing import Union

from solara.kitchensink import react, sol, w

if typing.TYPE_CHECKING:
    import numpy as np


@react.component
def Image(image: Union[str, Path, "np.ndarray"]):
    if isinstance(image, (str, Path)):
        path = Path(image)
        if path.exists():
            import ipywidgets

            format = ipywidgets.Image._guess_format("image", str(path))
            value = ipywidgets.Image._load_file_value(str(path))
            return w.Image(value=value, format=format)
        elif isinstance(image, str):
            url_data = image.encode("utf8")
            return w.Image(value=url_data, format="url")
    elif sol.util.isinstanceof(image, "numpy:ndarray"):
        value = sol.util.numpy_to_image(image, format="png")
        return w.Image(value=value, format="image/png")
    raise TypeError(f"Only support URL, path or numpy array, not {image}")
