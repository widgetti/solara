import base64
import os
from pathlib import Path

import solara as sol


def github_url(file):
    rel_path = os.path.relpath(file, Path(sol.__file__).parent.parent)
    github_url = sol.github_url + f"/blob/{sol.git_branch}/" + rel_path
    return github_url


def load_file_as_data_url(file_name, mime):
    with open(file_name, "rb") as f:
        data = f.read()
    return f"data:{mime};base64," + base64.b64encode(data).decode("utf-8")
