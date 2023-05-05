import typing
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Union

import solara
from solara.alias import rw

if typing.TYPE_CHECKING:
    import numpy as np
    import PIL.Image


@solara.component
def Image(
    image: Union[str, Path, "np.ndarray", bytes, "PIL.Image.Image"],
    width: Optional[str] = None,
    format="png",
    classes: List[str] = [],
):
    """Displays an image from a URL, Path, numpy data, bytes or PIL image.

    If passed as bytes, the image is assumed to be in the format specified by the `format` argument.

    ## Examples

    ### Displaying an image from a Path

    ```solara
    import solara
    import solara.website
    from pathlib import Path


    image_path = Path(solara.website.__file__).parent / "public/beach.jpeg"

    @solara.component
    def Page():
        solara.Image(image_path)
    ```

    ### Displaying an image from a URL

    ```solara
    import solara


    image_url = "/static/public/beach.jpeg"

    @solara.component
    def Page():
        solara.Image(image_url)
        display(image_url)

    ```

    ### Displaying an image from a numpy array

    ```solara

    import solara
    import solara.website
    from pathlib import Path
    import numpy as np
    import PIL.Image


    image_path = Path(solara.website.__file__).parent / "public/beach.jpeg"
    image_ndarray = np.asarray(PIL.Image.open(image_path))

    @solara.component
    def Page():
        solara.Image(image_ndarray)
        display(image_ndarray)
    ```

    ### Displaying an image from bytes

    ```solara

    import solara
    import solara.website
    from pathlib import Path
    import PIL.Image


    image_path = Path(solara.website.__file__).parent / "public/beach.jpeg"
    image_bytes = image_path.read_bytes()

    @solara.component
    def Page():
        solara.Image(image_bytes, format="jpeg")
        display(image_bytes[:100])
    ```

    ### Displaying an image from a PIL Image

    ```solara

    import solara
    import solara.website
    from pathlib import Path
    import PIL.Image


    image_path = Path(solara.website.__file__).parent / "public/beach.jpeg"
    image = PIL.Image.open(image_path)

    @solara.component
    def Page():
        solara.Image(image)
    ```


    ## Arguments
     * `image`: URL, Path, numpy data, bytes or PIL Image.
     * `width`: Width of the image, by default (None) the image is displayed at its original size.
        Other options are: "100%" (to full its parent size), "100px" (to display it at 100 pixels wide),
        or any other CSS width value.
     * `format`: Format of the image, only used when image is of type bytes, or a PIL Image is passed.
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
    elif isinstance(image, bytes):
        return rw.Image(
            value=image,
            format=format,
            _dom_classes=classes,  # type: ignore
            layout=layout,
        )
    elif solara.util.isinstanceof(image, "PIL.Image:Image"):
        f = BytesIO()
        image.save(f, format=format)  # type: ignore
        value = f.getvalue()
        return rw.Image(
            value=value,
            format="png",
            _dom_classes=classes,  # type: ignore
            layout=layout,
        )
    elif solara.util.isinstanceof(image, "numpy:ndarray"):
        value = solara.util.numpy_to_image(image, format="png")
        return rw.Image(
            value=value,
            format="png",
            _dom_classes=classes,  # type: ignore
            layout=layout,
        )
    raise TypeError(f"Only support URL, path or numpy array, not {image}")
