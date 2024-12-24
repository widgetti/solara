---
title: How to create a standalone binary (.exe file) with PyInstaller.
description: Create a standalone binary (.exe file) with PyInstaller similar to an Electron app, such as VSCode or Slack.
---
# How to create a standalone binary (.exe) with PyInstaller

PyInstaller is a tool that bundles a Python application and its dependencies into a single package. This package can be run on a different machine without needing to install Python or the dependencies. This is useful for distributing applications that run on the computer of a user, instead of a server, without needing to install Python on the user's machine.

Since Solara is a web framework, it also needs a browser to run. In this case, we are going to use Qt's integrated browser, to produce a fully standalone application, similar to an Electron app, such as VSCode or Slack.

Although in principle Electron could be used, by using Qt, we can have the browser and the server running in the same process, making it easier to create native menu items and have communication between the browser and the server.

## PyQt vs PySide

There are two Python libraries for using Qt: PyQt and PySide. PyQt is developed by Riverbank Computing and is available under two licenses: GPL and commercial. PySide is developed by the Qt Company and is available under the LGPL license. The LGPL license allows you to distribute the library with your application without needing to open-source your application. This is the license we are going to use in this example. Note that if you use the qtpy library, you can switch between PyQt and PySide without changing your code.


## Installation

```
# NOTE: the pefile version is pinned to avoid performance issue on windows at the time of writing
# see https://github.com/erocarrera/pefile/issues/420
pip install solara pyside6 qtpy pyinstaller "pefile<2024.8.26" click
```

## Solara app

We will use a very simply Solara app to demonstrate how to create a standalone binary.

Create a file called `app.py` with the following content:
```python
import solara

clicks = solara.reactive(0)


@solara.component
def Page():
    color = "green"
    if clicks.value >= 5:
        color = "red"

    def increment():
        clicks.value += 1
        print("clicks", clicks)  # noqa

    solara.Button(label=f"Clicked: {clicks}", on_click=increment, color=color)
```

Or run the following command to create the file:
```bash
 $ solara create button app.py
Wrote:  /home/myname/my-solara-project/app.py
Run as:
         $ solara run /home/myname/my-solara-project/app.py
```


## Application script

This part is responsible for interpreting the command line arguments, starting the Solara server, and creating the Qt application with the embedded browser that will render the Solara app.

Create a file called `my-solara-app.py` with the following content:
```python
import sys
from pathlib import Path

import click
import os

# make sure you use pyside when distributing your app without having to use a GPL license
from qtpy.QtWidgets import QApplication
from qtpy.QtWebEngineWidgets import QWebEngineView
from qtpy import QtCore

# make sure PyInstaller includes 'app.py'
import app


HERE = Path(__file__).parent


@click.command()
@click.option("--port", default=0, help="Port to run the server on, 0 for a random free port")
def run(port: int):
    os.environ["SOLARA_APP"] = "app"

    import solara.server.starlette

    server = solara.server.starlette.ServerStarlette(host="localhost", port=port)
    print(f"Starting server on {server.base_url}")
    server.serve_threaded()
    server.wait_until_serving()

    app = QApplication([""])
    web = QWebEngineView()
    web.setUrl(QtCore.QUrl(server.base_url))
    web.show()
    app.exec_()


if __name__ == "__main__":
    run()
```

You should now be able to run the application with the following command:
```bash
$ python my-solara-app.py
```

Which on MacOS should show up like this:

![Solara standalone app](https://solara-assets.s3.us-east-2.amazonaws.com/public/docs/howto/solara-qt.webp)


## Creating the standalone binary

Now that we have the application script, we can use PyInstaller to create a standalone binary.

```
$ pyinstaller my-solara-app.py --windowed
$ open ./dist/my-solara-app.app  # on MacOS
$ ./dist/my-solara-app.app/Contents/MacOS/my-solara-app  # on MacOS, but keeping the terminal open
```

This .app file can be distributed to other users, and they can run it without needing to install Python or any dependencies. Similarly, on Windows, you can distribute the .exe file or
create an installer, and on Linux, you can distribute the directory (possibly zipped).

However, for MacOS, you may need to sign the app to avoid the "unidentified developer" warning. Doing this is out the scope of this guide, but once you arrive at this point, you might want
to automate the process in CI. The [GitHub action workflow for Jdaviz](https://github.com/spacetelescope/jdaviz/blob/main/.github/workflows/standalone.yml) is a good example on how to set
this up. It does require an Apple Developer account however to do proper code signing.
