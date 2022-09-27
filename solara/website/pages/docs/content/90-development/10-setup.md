# Development


## Development setup

Assuming you have created a virtual environment as described in [the installation guide](/docs/guides/installing), you can install a development install of Solara using:

    $ git clone git@github.com:widgetti/solara.git
    $ cd solara
    $ pip install ".[server,develop,documentation]"  # documentation is optional


## Running Solara in dev mode

By passing the `--dev` flag, solara enters "dev" mode, which makes it friendlier for development

    $ solara run myscript.py --dev

This will:

    * Automatically restart the server if any of the source code of solara changes (excluding solara.website)
    * Load non-minified JS/CSS to make debugging easier)

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
