# Assets files

Asset files are special files with are loaded by Solara-server and thus have a special meaning, and come with defaults. Current supported assets files are:

 * `favicon.png` - Image shown by the browser (usually in the tab).
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


Although the `assets` directory can be used for serving arbitrary files, we recommend using the [static files](/docs/reference/static-files) directory instead, to avoid name collisions.
