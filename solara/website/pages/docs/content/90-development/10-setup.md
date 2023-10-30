# Development

See also [the contributing guide](/docs/howto/contribute) for more information on how to contribute to Solara.
## Development setup

Assuming you have created a virtual environment as described in [the installation guide](/docs/installing), you can install a development install of Solara using:

    $ git clone git@github.com:widgetti/solara.git
    $ cd solara
    $ pip install ".[dev,documentation]"  # documentation is optional


## Running Solara server in auto restart mode

By passing the `--auto-restart/-a` flag, the solara server will automatically restart when the sourcecode of the solara server changes, which makes it friendlier for development

    $ solara run myscript.py -a

This will:

    * Automatically restart the server if any of the source code of solara changes (excluding solara.website)

## Contributing

If you plan to contribute, also run the following:

    $ pre-commit install

This will cause a test of linters/formatters and mypy to run so the code is in good quality before you git commit.

    $ playwright install

This will install playwright, for when you want to run the integration tests.

### Test suite

If you want to run the unit tests (quick run when doing development, or when you do test driven development)

    $ py.test tests/unit


If you want to run the integration tests (uses playwright to open a browser to test the live server with a real browser)

    $ py.test tests/integration

Pass the `--headed` flag to see what is going on, [or check out the docs](https://playwright.dev/python/docs/intro)


### Creating a PR

Make sure you forked the repository, and set up the remote and origin correctly.

```
# rename origin to upstream
$ git remote rename origin upstream
# add your fork as origin
$ git remote add origin https://github.com/yourusername/solara.git
```

Now we will create a branch, push it, and open a PR

```
# create a branch
$ git checkout -b fix_some_thing
# add whatever changes you want to make
$ git add -p
# commit your changes
$ git commit -m "fix: some thing"
# push your changes
$ git push
# click the link that is printed to open a PR
```
