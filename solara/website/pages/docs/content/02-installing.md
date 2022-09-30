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
