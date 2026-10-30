# Versioning

This directory builds the `solara-assets2` package.
It replaced `solara-assets`, which hit the PyPI storage cap of 10 GB per project.

`solara-assets2` has its own version, not the solara version.
Bump it only when the assets change, which is when `packages` or the prune rules in `hatch_build.py` change.
`tests/unit/solara_assets_test.py` fails when you forget.
To bump:

1. Bump `__version__` in `solara_assets2/__init__.py`.
2. Change `content_hash` in the same file to the hash that the failing test prints.
3. Change the `solara-assets2==...` pin in `packages/solara-meta/pyproject.toml`.

The release CI publishes `solara-assets2` on every solara release, and skips the upload when that version is already on PyPI.

# Test a release

e.g. to manually make a release with a new solara-vuetify-app


```
$ cd packages/solara-vuetify-app
$ bump2version --verbose major
$ cd ../solara-assets
$ hatch build
# will fail downloading from cdn, so we fill the directory manually
$ tar zxfv ../solara-vuetify-app/widgetti-solara-vuetify-app-2.0.0.tgz  --strip-components=1 --directory cdn/@widgetti/solara-vuetify-app@2.0.0/
# build again
$ hatch build
```
