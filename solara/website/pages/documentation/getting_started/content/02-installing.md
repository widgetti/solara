---
title: Installing Solara
description: Installation should be as easy as running pip install Solara. Read on for advanced setups.
---
# Installation

## Create a virtual environment

It is best to install Solara into a virtual environment unless you know what you are doing (you already have a virtual environment, or you are using conda or docker).

See also [The Python Packaging User Guide](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#creating-a-virtual-environment) for more information about virtual environments.


### OSX/Unix/Linux

Setting up a virtual environment on OSX/Unix/Linux:

    $ python -m venv solara-env
    $ source ./solara-env/bin/activate

### Windows

Setting up a virtual environment on Windows:

    > py -m venv solara-env
    > solara-env\Scripts\activate


## Install Solara as a user

Now install Solara using pip:

    $ pip install solara

## Bleeding edge

If you want to install an unreleased version of Solara (e.g. because we just merged a feature you need)


```
$ pip install "solara @ git+https://github.com/widgetti/solara"
```

Or put the following in your `requirements.txt`:

```
solara @ https://github.com/widgetti/solara/package/archive/master.tar.gz

```

If you want to do development on Solara, read the [development documentation](/documentation/advanced/development/setup).

## Air-gapped installation / Firewalled network

If you want to have Solara running in an air-gapped environment or where access to a CDN is not possible due to firewall rules, you have two options


### Pre-install assets

Normally, Solara fetches assets (CSS, JavaScript and fonts) from a CDN on the fly, if that is not possible, you can pre-install the assets by running

```
$ pip install "solara[assets]"
```

### Airgapped install

If you cannot install `solara` or `solara-assets` from pypi because the server is not connected to the internet, you can
follow the following steps to install Solara:

```bash
# Download the required wheels from pypi.
$ pip wheel --wheel-dir solara-air-gapped "solara[assets]"
# Zip them in a tarball.
$ tar zcfv solara-air-gapped.tar.gz solara-air-gapped
# Copy the tarball to your server.
$ scp solara-air-gapped.tar.gz yourusername@youmachine:~/solara-air-gapped.tar.gz
# ssh into your server.
$ ssh yourusername@yourmachine
...
#  Unzip the tarball.
$ tar zxfv solara-air-gapped.tar.gz
# Install all wheels.
$ pip install solara-air-gapped/*.whl
```

## Solara subpackages

The `solara` package is a meta package that installs all the necessary dependencies to get started with Solara. By default, we install:

  * [`pip install "solara-ui[all]"`](https://pypi.org/project/solara-ui)
  * [`pip install "solara-server[starlette,dev]"`](https://pypi.org/project/solara-ui)

Note that the solara (meta) package will pin exact versions of solara-ui and solara-server, which ensures you always get compatible version of the subpackages.
For more flexibility, and control over what you install, you can install the subpackages directly.


### The `solara-ui` package

This package contains only the UI components, hooks and other utilities. This is the only package you need if you want to use Solara in a Jupyter environment. There are optional dependencies giving you
more control over what you want to install:

 * `pip install "solara-ui"` - Only the UI components, hooks and other utilities.
 * `pip install "solara-ui[markdown]"` - The above, with support for markdown rendering.
 * `pip install "solara-ui[cache]"` - The above, with support for [caching](https://solara.dev/docs/reference/caching)
 * `solara-ui[all]` - Installs all optional dependencies.

### The `solara-server` package

This will let you run solara applications outside a Jupyter server. See [Understanding Solara Server](https://solara.dev/documentation/advanced/understanding/solara-server) for more details about solara server.

For deployments, we recommend ``pip install "solara-server[starlette]"` which will install the starlette backend for solara server. For development, you can install the `dev` extra to get the development dependencies that enabled hot reloading.

The `solara-server` packages supports the following optional dependencies:

 * `pip install "solara-server"` - Only the solara server code with required dependencies, this in general is not a functional server (it needs starlette or flask to run).
 * `pip install "solara-server[starlette]"` - The solara server with the starlette backend.
 * `pip install "solara-server[flask]"` - The solara server with the starlette backend and development dependencies.
 * `pip install "solara-server[dev]"` - The solara server with dependencies for development for enabling hot reloading.
 * `pip install "solara-server[all]"` - Installs all optional dependencies.




### The `pytest-ipywidgets` package

This package is a plugin for pytest that lets you test ipywidgets with playwright. It is useful for testing your ipywidgets or solara applications in a (headless) browser.
See [Our testing documentation](https://solara.dev/documentation/advanced/howto/testing) for more information.

 * `pip install "pytest-ipywidgets"` - Minimal installation for testing ipywidgets.
 * `pip install "pytest-ipywidgets[voila]"` - The above, with a compatible version of voila.
 * `pip install "pytest-ipywidgets[jupyterlab]"` - The above, with a compatible version of jupyterlab.
 * `pip install "pytest-ipywidgets[notebook]"` - The above, with a compatible version of notebook.
 * `pip install "pytest-ipywidgets[all]"` - Installs all optional dependencies.
