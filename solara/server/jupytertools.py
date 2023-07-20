import json
from pathlib import Path
from typing import List

# based on notebook config, but to reduce the dependencies
# and with modern typing and use of pathlib


def recursive_update(target, new):
    """Recursively update one dictionary using another.

    None values will delete their keys.
    """
    for k, v in new.items():
        if isinstance(v, dict):
            if k not in target:
                target[k] = {}
            recursive_update(target[k], v)
            if not target[k]:
                # Prune empty subdicts
                del target[k]

        elif v is None:
            target.pop(k, None)

        else:
            target[k] = v


def _get_config(directory: Path, config_name: str):
    paths = [directory / f"{config_name}.json"]
    paths.extend((directory / f"{config_name}.d/").glob("*.json"))
    data: dict = {}
    for path in paths:
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                recursive_update(data, json.load(f))
    return data


def get_config(directories: List[Path], config_name: str):
    config: dict = {}
    # step through back to front, to ensure front of the list is top priority
    for directory in directories[::-1]:
        recursive_update(config, _get_config(directory, config_name))
    return config
