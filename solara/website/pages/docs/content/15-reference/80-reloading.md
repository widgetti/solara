# Reloading

## Reloading of Python files

Solara will auto detect if your script or the sourcecode of an imported module has changes. If so, Solara will reload the page.

(*Note: Upgrade to solara 1.14.0 for a fix in hot reloading using `pip install "solara>=1.14.0"`*)

## Reloading of .vue files

The solara server automatically watches all `.vue` files that are used by vue templates (there are some used in solara.components for example).
When a `.vue` file is saved, the widgets get updated automatically, without needing a page reload, aiding rapid development.

## Reloading of .vue files

The [Style component](/api/style) accepts a Path as argument, when that is used and the server is in development mode (the default), also
CSS files will be hot reloaded.


## Restarting the server after changes to the solara packages


You don't need to care about this feature if you only use solara, this is only relevant for development on solara itself, [see also development instructions](/docs/development).

If the `--auto-restart/-a` flag is passed to solara-server and any changes occur in the `solara` package (excluding `solara.webpage`), solara-server will restart. This speeds up development on `solara-server` for developers since you do not
need to manually restart the server in the terminal.

## Disabling reloading

In production mode (pass the `--production` argument to `solara run`) watching of files is disabled, and no reloading of files or vue templates will occur. If you run solara integrated in flask or uvicorn as laid out in [deployment documentation](https://solara.dev/docs/deploying/self-hosted)
