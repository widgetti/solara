from pathlib import Path


HERE = Path(__file__).parent


def get_hook_dirs():
    # used for pyinstaller
    return [str(HERE)]
