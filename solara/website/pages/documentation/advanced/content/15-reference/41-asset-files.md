---
title: Incorporating your assets, styles, and logos into your app
description: Solara looks for overrides of certain style and asset files in the assets folder by default. You can use these to incorporate your branding into your dashboard or app.
---
# Assets files

Asset files are special files with are loaded by Solara-server and thus have a special meaning, and come with defaults. Current supported assets files are:

 * `favicon.png` and/or `favicon.svg` - Image shown by the browser (usually in the tab). If SVG is not provided, default `favicon.svg` of the solara server may override your custom favicon.png depending on the browser. Providing both PNG and SVG versions is recommended.
 * `style.css` - Default `CSS` used by Solara.
 * `custom.css` - Custom `CSS` you can override for your project (empty `CSS` file by default).
 * `custom.js` - Custom Javascript you can use for your project (empty Javascript file by default).
 * `theme.js` - Javascript file containing the definitions for [vuetify themes](https://v2.vuetifyjs.com/en/features/theme/) ([example theme.js file](https://github.com/widgetti/solara/blob/master/solara/website/assets/theme.js)).


Assets files can be overridden by putting a file in the `../assets` directory.  A typical directory layout looks like this:

```
├── pages
│   ├── 01-landing-page.md
│   ├── 02-some_app.py
└── public
    └── beach.jpeg
└── assets
    ├── custom.css
    ├── custom.js
    ├── theme.js
    └── favicon.png
```

All assets files are served under `/static/assets/<filename>`, but how the assets go to the browser is considered an implementation detail (we could bundle/minimize the css for instance).

Putting the `assets` directory 1 level higher than the `pages` directory avoids name collision with pages.


Although the `assets` directory can be used for serving arbitrary files, we recommend using the [static files](/documentation/advanced/reference/static-files) directory instead, to avoid name collisions.


## Extra asset locations

If for instance you are creating a library on top of Solara, you might want to have your own assets files, like stylesheets or JavaScript files.
For this purpose, solara-server can be configured to look into other directories for assets files by setting the `SOLARA_ASSETS_EXTRA_LOCATIONS` environment variable.
This string contains a comma-separated list of directories or Python package names to look for asset files. The directories are searched in order, after looking in the application specific directory, and the first file found is used.

For example, if we run solara as:

```
$ export SOLARA_ASSETS_EXTRA_LOCATIONS=/path/to/assets,my_package.assets
$ solara run solara.website.pages
Solara server is starting at http://localhost:8765...
```

And we would fetch `http://localhost:8765/static/assets/my-image.jpg`, Solara-server would look for the file in the following order:

1. `.../solara/website/assets/my-image.jpg`
1. `/path/to/assets/my-image.jpg`
1. `.../my_package/assets/my-image.jpg`
1. `...site-package/solara/server/assets/my-image.jpg`

## Recommended pattern for libraries to add asset locations

If you are creating a library on top of Solara, and you want to programmatically add asset locations, you can do so by adding the following code to your library:

```python
import solara.server.settings
import my_package.assets


path = my_package.assets.__path__[0]
# append at the end, so SOLARA_ASSETS_EXTRA_LOCATIONS can override
solara.server.settings.assets.extra_locations.append(path)
```
