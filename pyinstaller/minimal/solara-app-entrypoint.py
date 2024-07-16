import click

# make sure pyinstaller picks it up
import sample_app  # noqa: F401
import os


@click.command()
@click.option(
    "--port",
    default=int(os.environ.get("PORT", 0)),
    help="Port to run the server on, 0 for a random free port",
)
@click.option(
    "--webview",
    default=False,
    is_flag=True,
    help="Run the app in a webview window",
)
def run(port: int, webview: bool = False):
    if "SOLARA_APP" not in os.environ:
        os.environ["SOLARA_APP"] = "sample_app"

    import solara.server.starlette

    server = solara.server.starlette.ServerStarlette(host="localhost", port=port)
    print(f"Starting server on {server.base_url}")
    server.serve_threaded()
    server.wait_until_serving()
    server.join()


if __name__ == "__main__":
    run()
