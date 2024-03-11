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
import uvicorn
from rich import print as rprint
from uvicorn.main import LEVEL_CHOICES, LOOP_CHOICES

import solara
from solara.server import settings

from .server import telemetry

try:
    from solara_enterprise.ssg import ssg_crawl
except ImportError:

    def ssg_crawl(*args, **kwargs):  # type: ignore
        raise RuntimeError('SSG not available, please install solara-enterprise (pip install "solara-enterprise[ssg]"')


HERE = Path(__file__).parent

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
        "reacton": {"handlers": ["default"], "level": "ERROR"},
        # "react": {"handlers": ["rich"], "level": "DEBUG"},
        "uvicorn": {"handlers": ["default"], "level": "ERROR"},
        "uvicorn.error": {"level": "ERROR"},
        "uvicorn.access": {"handlers": ["access"], "level": "ERROR", "propagate": False},
    },
}


def _check_version():
    import requests

    try:
        response = requests.get("https://pypi.org/pypi/solara/json")
        latest_version = response.json()["info"]["version"]
    except:  # noqa: E722
        return
    if latest_version != solara.__version__:
        print(f"New version of Solara available: {latest_version}. You have {solara.__version__}. Please upgrade using:")  # noqa: T201
        print(f'\t$ pip install "solara=={latest_version}"')  # noqa: T201


def find_all_packages_paths():
    paths = []
    # sitepackages = set([os.path.dirname(k) for k in site.getsitepackages()])
    sitepackages = {k for k in site.getsitepackages()}
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


production_default = False
if "SOLARA_MODE" in os.environ:
    # settings.main.mode by default is set to production,
    # which is a good default for when you embed in a flask
    # app for instance, but not for the CLI, which app developers
    # usually run.
    production_default = settings.main.mode == "production"
    # Note that in the CLI we do set this value to "development"
    # or "production" based on the --production flag


@cli.command()
@click.option("--port", default=int(os.environ.get("PORT", 8765)))
@click.option(
    "--host",
    default=settings.main.host,
    help="Host to listen on. Defaults to the $HOST environment or $SOLARA_HOST when available or localhost when not given.",
)
@click.option("--dev/--no-dev", default=None, help="Deprecated: use --auto-restart/-a", hidden=True)
@click.option("--production", is_flag=True, default=production_default, help="Run in production mode: https://solara.dev/docs/understanding/solara-server")
@click.option("--reload", is_flag=True, default=None, help="Deprecated: use --auto-restart/-a", hidden=True)
@click.option("-a", "--auto-restart", is_flag=True, default=False, help="Enable auto-restarting of server when the solara server code changes.")
@click.option("--tracer/--no-tracer", default=False)
@click.option("--timing/--no-timing", default=False)
@click.option("--open/--no-open", default=True)
@click.option(
    "--restart-dir",
    "restart_dirs",
    multiple=True,
    help="Set restart directories explicitly, instead of using the current working" " directory.",
    type=click.Path(exists=True),
)
@click.option(
    "--restart-exclude",
    "restart_excludes",
    multiple=True,
    help="Set glob patterns to exclude while watching for files. Includes "
    "'.*, .py[cod], .sw.*, ~*' by default; these defaults can be overridden "
    "with `--restart-include`. This option has no effect unless watchgod is "
    "installed.",
)
@click.option(
    "--workers",
    default=None,
    type=int,
    help="Number of worker processes. Defaults to the $WEB_CONCURRENCY environment" " variable if available, or 1. Not valid with --auto-restart/-a.",
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
    default=settings.theme.variant.name,
    help=f"Use light or dark variant, or auto detect (auto). [default: {settings.theme.variant.name}",
)
@click.option(
    "--dark",
    type=bool,
    default=settings.theme.variant == settings.ThemeVariant.dark,
    help="Use dark theme. Shorthand for --theme-variant=dark",
)
@click.option(
    "--theme-variant-user-selectable/--no-theme-variant-user-selectable",
    type=bool,
    hidden=True,
    help="Deprecated.",
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
@click.option(
    "--ssg/--no-ssg",
    is_flag=True,
    default=settings.ssg.enabled,
    help="(pre) Render static pages.",
)
@click.option(
    "--search/--no-search",
    is_flag=True,
    default=settings.search.enabled,
    help="Enable search (requires ssg generated pages).",
)
@click.option(
    "--check-version/--no-check-version",
    is_flag=True,
    default=True,
    help="Check installed version again pypi version.",
)
def run(
    app,
    host,
    port,
    open,
    auto_restart: bool,
    reload: bool,
    restart_dirs: typing.Optional[typing.List[str]],
    restart_excludes: typing.List[str],
    dev: bool,
    production: bool,
    tracer: bool,
    timing: bool,
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
    dark: bool,
    theme_variant_user_selectable: bool,
    ssg: bool,
    search: bool,
    check_version: bool = True,
):
    """Run a Solara app."""
    if dev is not None:
        print("solara: --dev is deprecated, use --auto-restart/-a instead", file=sys.stderr)  # noqa: T201
        auto_restart = dev
    if reload is not None:
        print("solara: --reload is deprecated, use --auto-restart/-a instead", file=sys.stderr)  # noqa: T201
        auto_restart = reload
    if check_version:
        _check_version()

    # uvicorn calls it reload, we call it auto restart
    reload = auto_restart
    del auto_restart
    settings.ssg.enabled = ssg
    settings.search.enabled = search
    reload_dirs = restart_dirs if restart_dirs else None
    del restart_dirs
    url = f"http://{host}:{port}"

    failed = False
    if reload:
        telemetry._auto_restart_enabled = True
        solara_root = Path(solara.__file__).parent

        reload_dirs = list(reload_dirs if reload_dirs else [])

        # we restart the server when solara or react changes, in principle we should do
        # that for all dependencies of the server, but these are changing most often
        # during development
        # We exclude the website, that will be handled by solara/server/reload.py
        reload_dirs = [str(solara_root), str(Path(solara.__file__).parent)]
        try:
            import solara_enterprise

            reload_dirs.append(str(Path(solara_enterprise.__file__).parent))
            del solara_enterprise
        except ImportError:
            pass
        reload_excludes = restart_excludes if restart_excludes else []
        del restart_excludes
        reload_excludes = [str(solara_root / "website"), str(solara_root / "template")]
        reload_excludes.append(app)
        del solara_root
        reload = True
        # avoid sending many restarts
        settings.telemetry.mixpanel_enable = False
    else:
        del restart_excludes

    if production:
        settings.main.mode = "production"
    else:
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
        # LOGGING_CONFIG["loggers"]["reacton"]["level"] = log_level.upper()

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
    if dark:
        theme_variant = settings.ThemeVariant.dark
    settings.theme.variant = theme_variant
    settings.main.tracer = tracer
    settings.main.timing = timing
    items = (
        "theme_variant_user_selectable dark theme_variant theme_loader use_pdb server open_browser open url failed dev tracer"
        " timing ssg search check_version production".split()
    )
    for item in items:
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

                ChangeReload(
                    config,
                    target=run_with_settings(
                        server, main=settings.main.dict(), theme=settings.theme.dict(), ssg=settings.ssg.dict(), search=settings.search.dict()
                    ),
                    sockets=[sock],
                ).run()
            else:
                server.run()
        except:  # noqa
            failed = True
            raise

    def ssg_run():
        while not failed and (server is None or not server.started):
            time.sleep(0.1)
        if not failed:
            assert server is not None
            base_url = f"http://{server.config.host}:{server.config.port}"
            rprint("Running Static Site Generator pre-render background task")
            ssg_crawl(base_url)
            if settings.search.enabled:
                from solara_enterprise.search.index import build_index

                build_index("")

    # in dev mode we run the ssg in the child process (see run_with_settings)
    if not dev and settings.ssg.enabled:
        threading.Thread(target=ssg_run, daemon=True).start()

    # if we don't have to wait for SSG, we can build the index right away
    if not settings.ssg.enabled and settings.search.enabled:
        from solara_enterprise.search.index import build_index

        build_index("")

    start_server()

    # TODO: if we want to use webview, it should be sth like this
    # server_thread = threading.Thread(target=start_server)
    # server_thread.start()
    # if open:
    #     # open_webview()
    #     open_browser()
    # server_thread.join()


@cli.command()
@click.argument("app")
@click.option("--port", default=int(os.environ.get("PORT", 8765)))
@click.option("--host", default=settings.main.host)
@click.option(
    "--headed/--no-headed",
    is_flag=True,
    default=settings.ssg.headed,
    help="Show browser window if true.",
)
def ssg(app: str, port: int, host: str, headed: bool):
    """Static site generation"""
    settings.ssg.headed = headed
    settings.ssg.enabled = True
    settings.main.mode = "production"  # always override this
    os.environ["SOLARA_APP"] = app
    from solara.server.starlette import ServerStarlette

    server = ServerStarlette(port=port, host=host)
    server.serve_threaded()
    server.wait_until_serving()

    base_url = f"http://{server.server.config.host}:{server.server.config.port}"

    ssg_crawl(base_url)


@cli.command()
def deploy():
    rprint("...")
    import time

    time.sleep(1)
    rprint("Want your app to run instantly on awesomeapp-mystartup-gh.solara.run?")
    rprint("\tCheck out https://solara.dev/docs/deploying/cloud-hosted")


@cli.command()
@click.argument("app")
def search(app: str):
    """Build search index based on ssg output"""
    os.environ["SOLARA_APP"] = app
    from solara_enterprise.search.index import build_index

    build_index("")


class run_with_settings:
    """This cross a process boundary, and takes the serialized settings with it"""

    def __init__(self, server: uvicorn.Server, main: typing.Dict, theme: typing.Dict, ssg: typing.Dict, search: typing.Dict):
        self.server = server
        self.main = main
        self.theme = theme
        self.ssg = ssg
        self.search = search

    def __call__(self, *args, **kwargs):
        # this is now in the new process, where we need to re-apply the settings
        failed = False

        def ssg_run():
            while not failed and (self.server is None or not self.server.started):
                time.sleep(0.1)
            if not failed:
                assert self.server is not None
                base_url = f"http://{self.server.config.host}:{self.server.config.port}"
                rprint("Running Static Site Generator pre-render background task")
                ssg_crawl(base_url)
                if settings.search.enabled:
                    from solara_enterprise.search.index import build_index

                    build_index("")

        settings.main = settings.MainSettings(**self.main)
        settings.theme = settings.ThemeSettings(**self.theme)
        settings.ssg = settings.SSG(**self.ssg)
        settings.search = settings.Search(**self.search)
        if settings.ssg.enabled:
            threading.Thread(target=ssg_run, daemon=True).start()
        try:
            return self.server.run(*args, **kwargs)
        except:  # noqa
            failed = True
            raise


@cli.command()
@click.option("--port", default=int(os.environ.get("PORT", 8000)))
def staticserve(port):
    """Experimental static serving"""
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
    import solara.server.server

    server_path = HERE / "server"
    assets_path = server_path / "assets"
    static_path = server_path / "static"

    target_dir = Path("staticbuild")
    target_dir.mkdir(exist_ok=True)

    from .server import settings

    copytree(settings.assets.proxy_cache_dir, target_dir / "_solara/cdn/")

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
        nbextensions, ignore = solara.server.server.get_nbextensions()
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

    target_dir_static_dist = target_dir / "static/dist"
    target_dir_static_dist.mkdir(exist_ok=True)
    voila = server_path / "dist"
    for path in list(voila.glob("*.js")) + list(voila.glob("*.woff")):
        shutil.copy(path, target_dir_static_dist)

    index_html = solara.server.server.read_root("", render_kwargs={"for_pyodide": True}, use_nbextensions=True)
    assert index_html is not None
    (target_dir / "index.html").write_text(index_html)


@click.group()
def create():
    """Quickly create a solara script or project."""
    pass


@create.command()
@click.argument(
    "target",
    type=click.Path(exists=False),
    default="sol.py",
    required=False,
)
def button(target: typing.Optional[Path]):
    """Create a button with a click counter."""
    write_script("button", target)


@create.command()
@click.argument(
    "target",
    type=click.Path(exists=False),
    default="sol.py",
    required=False,
)
def markdown(target: typing.Optional[Path] = None):
    """Create a markdown editor."""
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


# recursively copy a directory and allow for existing directories
def copytree(src: Path, dst: Path, copy_function=shutil.copy2, ignore: typing.Callable[[Path], bool] = lambda x: False, rename=lambda x: x):
    print(src, " -> ", dst)  # noqa
    if not src.exists():
        return
    if not dst.exists():
        dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if ignore(item):
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
    """Create a full Python project template for a data portal"""
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
cli.add_command(ssg)


def main():
    cli()


if __name__ == "__main__":
    main()
