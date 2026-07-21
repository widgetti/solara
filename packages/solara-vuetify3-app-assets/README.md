# solara-vuetify3-app-assets

This data-only companion wheel contains the prebuilt
`@widgetti/solara-vuetify3-app` frontend. It installs the bundle into
`share/solara/cdn`, where Solara's local CDN handler can serve it without
downloading the npm package from a public CDN.

Build the frontend first, then build this package:

```shell
(cd ../solara-vuetify3-app && npm run build)
hatch build -t wheel
```

The Python distribution version tracks the Solara release. The embedded CDN
directory independently tracks the frontend version from
`../solara-vuetify3-app/package.json`. This wheel is built from the Solara
monorepo and intentionally does not publish a standalone source distribution.
