# Reloading

## Reloading of Python files

Solara will auto detect if your script or the sourcecode of an imported module has changes. If so, Solara will reload the page.

(*Note: Upgrade to solara 1.14.0 for a fix in hot reloading using `pip install "solara>=1.14.0"`*)

## Reloading of .vue files

The solara server automatically watches all `.vue` files that are used by vue templates (there are some used in solara.components for example).
When a `.vue` file is saved, the widgets get updated automatically, without needing a page reload, aiding rapid development.


## Reloading after changes to the solara packages


You don't need to care about this feature if you only use solara, this is only relevant for development on solara itself, [see also development instructions](/docs/development).

If the `--dev` flag is passed to solara-server, if any changes occur in the `solara` package (excluding `solara.webpage`), solara-server will restart. This takes slightly longer, but speeds up development on `solara-server` itself for developers.
