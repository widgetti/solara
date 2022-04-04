import logging
import os
import site
import sys
import threading
import time
import typing
import webbrowser

import rich_click as click
import uvicorn
from uvicorn.main import LEVEL_CHOICES, LOG_LEVELS

HOST_DEFAULT = os.environ.get("HOST", "localhost")
if "arm64-apple-darwin" in HOST_DEFAULT:  # conda activate script
    HOST_DEFAULT = "localhost"

LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',  # noqa: E501
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "rich": {
            "class": "rich.logging.RichHandler",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "solara": {"handlers": ["rich"], "level": "INFO"},
        "uvicorn": {"handlers": ["default"], "level": "ERROR"},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    },
}


def find_all_packages_paths():
    paths = []
    # sitepackages = set([os.path.dirname(k) for k in site.getsitepackages()])
    sitepackages = set([k for k in site.getsitepackages()])
    paths.extend(list(sitepackages))
    print(sitepackages)
    for name, module in sys.modules.items():
        if hasattr(module, "__path__"):
            try:
                path = module.__path__[0]
            except:  # noqa: E722
                pass  # happens for namespace packages it seems
                # print(f"Error for {name}")
                # if path:
                #     skip = False
                #     for sitepackage in sitepackages:
                #         if path.startswith(sitepackage):
                #             skip = True
                # if not skip:
                # print(name, path, skip)
                paths.append(str(path))
    # print("PATHS", paths)
    return paths


@click.command()
@click.option("--port", default=int(os.environ.get("PORT", 8765)))
@click.option("--host", default=HOST_DEFAULT)
@click.option("--dev/--no-devn", default=False)
@click.option("--open/--no-open", default=False)
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload.")
@click.option(
    "--reload-dir",
    "reload_dirs",
    multiple=True,
    help="Set reload directories explicitly, instead of using the current working" " directory.",
    type=click.Path(exists=True),
)
@click.option(
    "--reload-exclude",
    "reload_excludes",
    multiple=True,
    help="Set glob patterns to exclude while watching for files. Includes "
    "'.*, .py[cod], .sw.*, ~*' by default; these defaults can be overridden "
    "with `--reload-include`. This option has no effect unless watchgod is "
    "installed.",
)
@click.option(
    "--workers",
    default=None,
    type=int,
    help="Number of worker processes. Defaults to the $WEB_CONCURRENCY environment" " variable if available, or 1. Not valid with --reload.",
)
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    default=None,
    help="Environment configuration file.",
    show_default=True,
)
@click.option(
    "--log-config",
    type=click.Path(exists=True),
    default=None,
    help="Logging configuration file. Supported formats: .ini, .json, .yaml.",
    show_default=True,
)
@click.option(
    "--log-level",
    type=LEVEL_CHOICES,
    default=None,
    help="Log level. [default: info]",
    show_default=True,
)
@click.option(
    "--log-level-uvicorn",
    type=LEVEL_CHOICES,
    default="error",
    help="Log level. [default: error]",
    show_default=True,
)
@click.option(
    "--access-log/--no-access-log",
    is_flag=True,
    default=True,
    help="Enable/Disable access log.",
)
@click.option(
    "--root-path",
    type=str,
    default="",
    help="Set the ASGI 'root_path' for applications submounted below a given URL path.",
)
@click.argument("app")
def main(
    app,
    host,
    port,
    open,
    reload: bool,
    reload_dirs: typing.Optional[typing.List[str]],
    dev: bool,
    reload_excludes: typing.List[str],
    workers: int,
    env_file: str,
    root_path: str,
    log_config: str,
    log_level: str,
    log_level_uvicorn: str,
    access_log: bool,
):
    reload_dirs = reload_dirs if reload_dirs else None
    url = f"http://{host}:{port}"

    failed = False
    if dev:
        reload_dirs = reload_dirs if reload_dirs else []
        reload_dirs = list(reload_dirs) + list(find_all_packages_paths())
        reload = True

    def open_browser():
        import socket

        s = socket.socket()
        for i in range(100):
            if failed:
                return
            try:
                s.connect((host, port))
                break
            except Exception as e:
                print(f"Server is not running get, will try again soon: {e}")
            time.sleep(1)

        print(f"Server is up, opening page {url}, disable this option by passing the --no-open argument to solara")
        webbrowser.open(url)

    if open:
        threading.Thread(target=open_browser, daemon=True).start()

    if log_level is not None:
        if isinstance(log_level, str):
            log_level = LOG_LEVELS[log_level]
        else:
            log_level = log_level
        logging.getLogger("uvicorn.error").setLevel(log_level)
        logging.getLogger("uvicorn.access").setLevel(log_level)
        logging.getLogger("uvicorn.asgi").setLevel(log_level)
    log_level = log_level_uvicorn
    del log_level_uvicorn

    kwargs = locals().copy()
    os.environ["SOLARA_APP"] = app
    kwargs["app"] = "solara.server.fastapi:app"
    kwargs["log_config"] = LOGGING_CONFIG if log_config is None else log_config
    for item in "open_browser open url failed dev".split():
        del kwargs[item]
    try:
        uvicorn.run(**kwargs)
    finally:
        failed = True


if __name__ == "__main__":
    main()
