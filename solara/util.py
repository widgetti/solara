import base64
import contextlib
import os
import sys
from collections import abc
from pathlib import Path
from typing import Dict, List, Union

import numpy as np
import PIL.Image

import solara


def github_url(file):
    rel_path = os.path.relpath(file, Path(solara.__file__).parent.parent)
    github_url = solara.github_url + f"/blob/{solara.git_branch}/" + rel_path
    return github_url


def github_edit_url(file):
    # e.g. https://github.com/widgetti/solara/edit/master/solara/__init__.py
    rel_path = os.path.relpath(file, Path(solara.__file__).parent.parent)
    github_url = solara.github_url + f"/edit/{solara.git_branch}/" + rel_path
    return github_url


def load_file_as_data_url(file_name, mime):
    with open(file_name, "rb") as f:
        data = f.read()
    return f"data:{mime};base64," + base64.b64encode(data).decode("utf-8")


def isinstanceof(object, spec: str):
    """Check if object is instance of type '<modulename>:<classname>'

    This can avoid a runtime dependency, since we do not need to import `modulename`.

    >>> import numpy as np
    >>> isinstanceof(np.arange(2), "numpy:ndarray")
    True
    """
    module_name, classname = spec.split(":")
    module = sys.modules.get(module_name)
    if module:
        cls = getattr(module, classname)
        return isinstance(object, cls)
    return False


def numpy_to_image(data: "np.ndarray", format="png"):
    import io

    if data.ndim == 3:
        if data.shape[2] == 3:
            im = PIL.Image.fromarray(data[::], "RGB")
        elif data.shape[2] == 4:
            im = PIL.Image.fromarray(data[::], "RGBA")
        else:
            raise ValueError(f"Expected last dimension to have 3 or 4 dimensions, total shape we got was {data.shape}")
        f = io.BytesIO()
        im.save(f, format)
        return f.getvalue()
    else:
        raise ValueError(f"Expected an image with 3 dimensions (height, width, channel), not {data.shape}")


@contextlib.contextmanager
def cwd(path):
    cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


def numpy_equals(a, b):
    if a is b:
        return True
    if a is None or b is None:
        return False
    if np.all(a == b):
        return True
    return False


def _combine_classes(class_list: List[str]) -> str:
    return " ".join(class_list)


def _flatten_style(style: Union[str, Dict, None] = None) -> str:
    if style is None:
        return ""
    elif isinstance(style, str):
        return style
    elif isinstance(style, dict):
        return ";".join(f"{k}:{v}" for k, v in style.items())
    else:
        raise ValueError(f"Expected style to be a string or dict, got {type(style)}")


def import_item(name: str):
    """Import an object by name like solara.cache.LRU"""
    parts = name.rsplit(".", 2)
    if len(parts) == 1:
        return __import__(name)
    else:
        module = __import__(".".join(parts[:-1]), fromlist=[parts[-1]])
        return getattr(module, parts[-1])


def get_solara_home() -> Path:
    """Get solara home directory, defaults to $HOME/.solara.

    The $SOLARA_HOME environment variable can be set to override this default.

    If both $SOLARA_HOME and $HOME are not defined, the current working directory is used.
    """
    if "SOLARA_HOME" in os.environ:
        return Path(os.environ["SOLARA_HOME"])
    elif "HOME" in os.environ:
        return Path(os.path.join(os.environ["HOME"], ".solara"))
    else:
        return Path(os.getcwd())


def parse_size(size: str) -> int:
    """Given a human readable size, return the number of bytes.

    Supports GB, MB, KB, and bytes. E.g. 10GB, 500MB, 1KB, 1000

    Commas and _ are ignored, e.g. 1,000,000 is the same as 1000000.
    """
    size = size.replace(",", "").replace("_", "").upper()
    if size.endswith("GB"):
        return int(float(size[:-2]) * 1024 * 1024 * 1024)
    elif size.endswith("MB"):
        return int(float(size[:-2]) * 1024 * 1024)
    elif size.endswith("KB"):
        return int(float(size[:-2]) * 1024)
    elif size.endswith("B"):
        return int(float(size[:-1]))
    else:
        return int(size)


def nested_get(object, dotted_name: str, default=None):
    names = dotted_name.split(".")
    for name in names:
        if isinstance(object, abc.Mapping):
            if name == names[-1]:
                object = object.get(name, default)
            else:
                object = object.get(name)
        else:
            if name == names[-1]:
                object = getattr(object, name, default)
            else:
                object = getattr(object, name)
    return object
