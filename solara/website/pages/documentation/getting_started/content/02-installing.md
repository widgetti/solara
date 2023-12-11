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

If you want to do development on Solara, read the [development documentation](/docs/development).

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
