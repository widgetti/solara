import sys
import threading
from time import sleep
from pathlib import Path

import click
import os


HERE = Path(__file__).parent


@click.command()
@click.option(
    "--port",
    default=int(os.environ.get("PORT", 0)),
    help="Port to run the server on, 0 for a random free port",
)
def run(port: int):
    os.environ["SOLARA_APP"] = str(HERE / "test_app.py")

    import webview
    import solara.server.starlette

    server = solara.server.starlette.ServerStarlette(host="localhost", port=5001)
    print(f"Starting server on {server.base_url}")
    server.serve_threaded()
    server.wait_until_serving()

    def test(value):
        print("test output", value)
        window.destroy()
        sys.exit(0)

    def fail_guard():
        sleep(15)
        # dump html
        html = window.evaluate_js("document.documentElement.outerHTML")
        window.destroy()
        print("failed")
        if html:
            print("html", html)
            with open("test-results/pywebview-failed.html", "w") as f:
                f.write(html)
        else:
            print("no html")
        sys.exit(1)

    threading.Thread(target=fail_guard, daemon=True).start()
    window = webview.create_window("Solara example app", server.base_url)  # , resizable=True, width=1500, height=1500)#, on_top=True)
    window.expose(test)
    webview.start()
    # server.join()


if __name__ == "__main__":
    run()
