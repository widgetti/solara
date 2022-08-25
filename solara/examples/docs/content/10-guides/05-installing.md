# Installation

## Create a virtual environment

It is best to install Solara into a virtual environment unless you know what you are doing (you already have a virtual environment, or you are using conda or docker).

See also [The Python Packaging User Guide](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#creating-a-virtual-environment) for more information.


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

    $ pip install solara[server,examples] watchdog

## Development

Go to [development documentation](/docs/development) if you want to develop on Solara, or you want to run the master branch, you can follow these steps:

First clone the repo:

    $ git clone git@github.com:widgetti/solara.git

Now install Solara in 'edit' mode. We use flit (`pip install flit` if you don't already have it)

    $ cd solara
    $ flit install --pth-file --deps develop --extras server,examples
    $ pip install watchdog  # to get hot reloading

Now you can edit the source code in the git repository, without having to reinstall it.
