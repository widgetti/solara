import os
import shutil
import site
import sys
import threading
import time
import typing
import webbrowser
from enum import Enum
from pathlib import Path

import rich
import rich_click as click
import solara
import uvicorn
from rich import print as rprint
from uvicorn.main import LEVEL_CHOICES, LOOP_CHOICES

from .server import settings

HERE = Path(__file__).parent
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
        "solara": {"handlers": ["default"], "level": "ERROR"},
        "react": {"handlers": ["default"], "level": "ERROR"},
        # "react": {"handlers": ["rich"], "level": "DEBUG"},
        "uvicorn": {"handlers": ["default"], "level": "ERROR"},
        "uvicorn.error": {"level": "ERROR"},
        "uvicorn.access": {"handlers": ["access"], "level": "ERROR", "propagate": False},
    },
}


def find_all_packages_paths():
    paths = []
    # sitepackages = set([os.path.dirname(k) for k in site.getsitepackages()])
    sitepackages = set([k for k in site.getsitepackages()])
    paths.extend(list(sitepackages))
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


class EnumType(click.Choice):
    def __init__(self, enum: typing.Type[Enum], case_sensitive=False):
        self._enum = enum
        super().__init__(choices=[item.name for item in enum], case_sensitive=case_sensitive)


@click.group()
def cli():
    pass


@cli.command()
@click.option("--port", default=int(os.environ.get("PORT", 8765)))
@click.option("--host", default=HOST_DEFAULT)
@click.option(
    "--dev/--no-dev",
    default=False,
    help="""Tell Solara to work in production(default) or development mode.
When in dev mode Solara will:
  Auto reload server when the server code changes
  Prefer non-minized js/css assets for easier debugging.
""",
)
@click.option("--tracer/--no-tracer", default=False)
@click.option("--timing/--no-timing", default=False)
@click.option("--open/--no-open", default=True)
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
@click.option(
    "--theme-loader",
    type=str,
    default=settings.theme.loader,
    help=f"Loader to use when the app is not yet shown to the user. [default: {settings.theme.loader!r}]",
)
@click.option(
    "--theme-variant",
    type=settings.ThemeVariant,
    default=settings.ThemeVariant.light.name,
    help=f"Use light or dark variant, or auto detect (auto). [default: {settings.theme.variant.name}",
)
@click.option(
    "--theme-variant-user-selectable/--no-theme-variant-user-selectable",
    type=bool,
    default=settings.theme.variant_user_selectable,
    help=f"Can the user select the theme variant from the UI. [default: {settings.theme.variant_user_selectable}",
)
@click.option("--pdb/--no-pdb", "use_pdb", default=False, help="Enter debugger on error")
@click.argument("app")
@click.option(
    "--loop",
    type=LOOP_CHOICES,
    default="auto",
    help="Event loop implementation.",
    show_default=True,
)
def run(
    app,
    host,
    port,
    open,
    reload: bool,
    reload_dirs: typing.Optional[typing.List[str]],
    dev: bool,
    tracer: bool,
    timing: bool,
    reload_excludes: typing.List[str],
    loop: str,
    workers: int,
    env_file: str,
    root_path: str,
    log_config: str,
    log_level: str,
    log_level_uvicorn: str,
    access_log: bool,
    use_pdb: bool,
    theme_loader: str,
    theme_variant: settings.ThemeVariant,
    theme_variant_user_selectable: bool,
):
    reload_dirs = reload_dirs if reload_dirs else None
    url = f"http://{host}:{port}"

    failed = False
    if dev:
        solara_root = Path(solara.__file__).parent

        reload_dirs = list(reload_dirs if reload_dirs else [])

        # we restart the server when solara or react changes, in priciple we should do
        # that for all dependencies of the server, but these are changing most often
        # during development
        # We exclude exampes, that will be handled by solara/server/reload.py
        reload_dirs = [str(solara_root), str(Path(solara.__file__).parent)]
        reload_excludes = reload_excludes if reload_excludes else []
        reload_excludes = [str(solara_root / "website")]
        del solara_root
        reload = True
        settings.main.mode = "development"

    server = None

    # TODO: we might want to support this, but it needs to be started from the main thread
    # and then uvicorn needs to be started from a thread
    # def open_webview():
    #     import webview

    #     while not failed and (server is None or not server.started):
    #         time.sleep(0.1)
    #     if not failed:
    #         window = webview.create_window("Hello world", url, resizable=True)
    #         window.on_top = True
    #         # window.show()
    #         webview.start(debug=True)

    def open_browser():
        while not failed and (server is None or not server.started):
            time.sleep(0.1)
        if not failed:
            webbrowser.open(url)

    if open:
        threading.Thread(target=open_browser, daemon=True).start()
    rich.print(f"Solara server is starting at {url}")

    if log_level is not None:
        LOGGING_CONFIG["loggers"]["solara"]["level"] = log_level.upper()
        # LOGGING_CONFIG["loggers"]["react"]["level"] = log_level.upper()

    log_level = log_level_uvicorn
    del log_level_uvicorn

    kwargs = locals().copy()
    # cgi vars: https://datatracker.ietf.org/doc/html/rfc3875
    os.environ["SOLARA_APP"] = app
    os.environ["SERVER_NAME"] = host
    os.environ["SERVER_PORT"] = str(port)

    kwargs["app"] = "solara.server.starlette:app"
    kwargs["log_config"] = LOGGING_CONFIG if log_config is None else log_config
    kwargs["loop"] = loop
    settings.main.use_pdb = use_pdb
    settings.theme.loader = theme_loader
    settings.theme.variant = theme_variant
    settings.theme.variant_user_selectable = theme_variant_user_selectable
    settings.main.tracer = tracer
    settings.main.timing = timing
    for item in "theme_variant_user_selectable theme_variant theme_loader use_pdb server open_browser open url failed dev tracer timing".split():
        del kwargs[item]

    def start_server():
        nonlocal server
        nonlocal failed
        try:
            # we manually create the server instead of calling uvicorn.run
            # because we can then access the server variable and check if it is
            # running.
            config = uvicorn.Config(**kwargs)
            server = uvicorn.Server(config=config)
            if reload:
                sock = config.bind_socket()
                from uvicorn.supervisors import ChangeReload

                ChangeReload(config, target=run_with_settings(server, main=settings.main.dict(), theme=settings.theme.dict()), sockets=[sock]).run()
            else:
                server.run()
        except:  # noqa
            failed = True
            raise

    start_server()

    # TODO: if we want to use webview, it should be sth like this
    # server_thread = threading.Thread(target=start_server)
    # server_thread.start()
    # if open:
    #     # open_webview()
    #     open_browser()
    # server_thread.join()


class run_with_settings:
    """This cross a process boundry, and takes the serialized settings with it"""

    def __init__(self, server: uvicorn.Server, main: typing.Dict, theme: typing.Dict):
        self.server = server
        self.main = main
        self.theme = theme

    def __call__(self, *args, **kwargs):
        # this is now in the new process, where we need to re-apply the settings
        settings.main = settings.MainSettings(**self.main)
        settings.theme = settings.ThemeSettings(**self.theme)
        return self.server.run(*args, **kwargs)


@cli.command()
@click.option("--port", default=int(os.environ.get("PORT", 8000)))
def staticserve(port):
    import http.server
    import os
    from functools import partial

    print(f"http://localhost:{port}/")  # noqa
    wk_dir = os.getcwd() + "/staticbuild"
    http.server.SimpleHTTPRequestHandler.extensions_map[".js"] = "application/javascript"
    http.server.SimpleHTTPRequestHandler.extensions_map = {k: v + ";charset=UTF-8" for k, v in http.server.SimpleHTTPRequestHandler.extensions_map.items()}
    http.server.test(HandlerClass=partial(http.server.SimpleHTTPRequestHandler, directory=wk_dir), port=port, bind="")  # type: ignore


@cli.command()
def staticbuild():
    """Experimental static build"""
    # imports locals, otherwise .run() does not use the cli arguments
    import solara.server
    import solara.server.patch
    import solara.server.server

    server_path = HERE / "server"
    assets_path = server_path / "assets"
    static_path = server_path / "static"

    target_dir = Path("staticbuild")
    target_dir.mkdir(exist_ok=True)

    from .server import cdn_helper

    copytree(cdn_helper.default_cache_dir, target_dir / "_solara/cdn/")

    static_dir_target = target_dir / "static"
    static_dir_target.mkdir(exist_ok=True)

    assets_dir_target = target_dir / "static" / "assets"
    assets_dir_target.mkdir(exist_ok=True)
    copytree(assets_path, assets_dir_target)

    for path in (
        list(static_path.glob("*.css"))
        + list(static_path.glob("*.js"))
        + list(static_path.glob("*.ps"))
        + list(static_path.glob("*.py"))
        + list(static_path.glob("*.png"))
        + list(static_path.glob("*.svg"))
    ):
        shutil.copy(path, static_dir_target)

    include_nbextensions = True
    if include_nbextensions:
        directories = solara.server.server.get_nbextensions_directories()
        nbextensions = solara.server.server.get_nbextensions()
        for name in nbextensions:
            for directory in directories:
                if (directory / (name + ".js")).exists():
                    src = (directory / (name + ".js")).parent
                    dst: Path = (static_dir_target / "nbextensions" / (name + ".js")).parent
                    dst.mkdir(parents=True, exist_ok=True)
                    # shutil.copytree(src, dst)
                    copytree(src, dst)

    target_dir_wheels = target_dir / "wheels"
    target_dir_wheels.mkdir(exist_ok=True)
    version = solara.__version__
    for path in [Path(f"dist/solara-{version}-py2.py3-none-any.whl")]:
        shutil.copy(path, target_dir_wheels)

    target_dir_nbconvert_static = target_dir / "static/nbconvert"
    target_dir_nbconvert_static.mkdir(exist_ok=True, parents=True)
    nbconvert = Path(solara.server.server.nbconvert_static)
    for path in list(nbconvert.glob("*.js")) + list(nbconvert.glob("*.css")):
        shutil.copy(path, target_dir_nbconvert_static)

    target_dir_static_dist = target_dir / "static/dist"
    target_dir_static_dist.mkdir(exist_ok=True)
    voila = server_path / "dist"
    for path in list(voila.glob("*.js")) + list(voila.glob("*.woff")):
        shutil.copy(path, target_dir_static_dist)

    solara.server.patch.patch()
    index_html = solara.server.server.read_root("", render_kwargs={"for_pyodide": True}, use_nbextensions=True)
    (target_dir / "index.html").write_text(index_html)


@click.group()
def create():
    pass


@create.command()
@click.argument(
    "target",
    type=click.Path(exists=False),
    default="sol.py",
    required=False,
)
def button(target: typing.Optional[Path]):
    write_script("button", target)


@create.command()
@click.argument(
    "target",
    type=click.Path(exists=False),
    default="sol.py",
    required=False,
)
def markdown(target: typing.Optional[Path] = None):
    write_script("markdown", target)


def write_script(name: str, target: typing.Optional[Path]):
    code = (HERE / "template" / f"{name}.py").read_text()
    if target is None:
        target = Path("sol.py")
    else:
        target = Path(target)
    target.parent.mkdir(exist_ok=True)
    target.write_text(code)
    rprint(f"Wrote:  {target.resolve()}")
    rprint(f"Run as:\n\t $ solara run {target.resolve()}")


# recursivly copy a directory and allow for existing directories
def copytree(src: Path, dst: Path, copy_function=shutil.copy2, ignore: typing.Callable[[Path], bool] = lambda x: False, rename=lambda x: x):
    print(src, " -> ", dst)  # noqa
    if not src.exists():
        return
    if not dst.exists():
        dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if ignore and ignore(item):
            continue
        if item.is_dir():
            copytree(item, dst / rename(item).name, ignore=ignore, copy_function=copy_function, rename=rename)
        else:
            copy_function(item, dst / rename(item).name)


@create.command()
@click.argument(
    "target",
    type=click.Path(exists=False),
    default="solara_portal",
    required=False,
)
def portal(target: Path):
    target = Path(target)
    name = target.name
    package_name = name.replace("-", "_")

    def copy_function(src: Path, dst: Path):
        dst.write_bytes(
            src.read_bytes().replace(b"solara-portal", name.encode("utf8")).replace(b"solara_portal", package_name.encode("utf8")),
        )

    def rename(path: Path):
        if path.name == "solara_portal":
            return path.parent / package_name
        else:
            return path

    copytree(
        HERE / "template" / "portal",
        target,
        ignore=lambda p: p.name.startswith("__") and p.name != "__init__.py",
        copy_function=copy_function,
        rename=rename,
    )
    rprint(f"Wrote:  {target.resolve()}")
    rprint(f"Install as:\n\t $ (cd {target}; pip install -e .)")
    rprint(f"Run as:\n\t $ solara run {package_name}.pages")


cli.add_command(run)
cli.add_command(staticbuild)
cli.add_command(create)


def main():
    cli()


if __name__ == "__main__":
    main()
