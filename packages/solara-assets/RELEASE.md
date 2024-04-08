# Stable

Version of solara-assets is locked to solara, and released in CI.

# Test a release

e.g. to manually make a release with a new solara-vuetify-app


```
$ cd packages/solara-vuetify-app
$ bump2version --verbose major
$ cd ../assets
$ batch build
# will fail downloading from cdn, so we fill the directory manually
$ tar zxfv ../solara-vuetify-app/widgetti-solara-vuetify-app-2.0.0.tgz  --strip-components=1 --directory cdn/@widgetti/solara-vuetify-app@2.0.0/
# build again
$ batch build
```
