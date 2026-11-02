# Versioning

This directory builds the `solara-assets2` package.
It replaced `solara-assets`, which hit the PyPI storage cap of 10 GB per project.

`solara-assets2` has its own version, not the solara version.
Bump it only when the wheel changes, for example when `packages` or the prune rules in `hatch_build.py` change.
The `Check that changed solara-assets2 content has a new version` step in CI fails when the wheel differs from the wheel on PyPI with the same version.
A release of `solara-vuetify-app` or `solara-vuetify3-app` changes `hatch_build.py`, so it always needs this bump.
To bump:

1. Bump `__version__` in `solara_assets2/__init__.py`.
2. Change the `solara-assets2==...` pin in `packages/solara-meta/pyproject.toml`.

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
