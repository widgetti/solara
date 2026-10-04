import * as Vue from 'vue';

import * as solara from './solara';

// The frontend features of this bundle, next to the ones of the widget manager.
// Vuetify (JS) is a chunk: a page without it uses a pure Vue shell. Its CSS is the
// feature vuetify-css.
// Vuetify's icons use mdi, its typography uses Roboto, and it needs its CSS, so a lazy
// Vuetify loads them too (into their CSS slots, the place of a preloaded link). An app with
// its own font leaves Roboto out with "-roboto" in --frontend, and an app with its own
// Vuetify CSS leaves Vuetify's out with "-vuetify-css": the page's normalized spec, where
// the last "+name" or "-name" wins (as in solara/server/frontend.py).
function leftOut(name) {
    const spec = (window.solaraFrontend && window.solaraFrontend.spec) || '';
    const tokens = spec.split(',');
    return tokens.lastIndexOf('-' + name) > tokens.lastIndexOf('+' + name);
}
solara.registerFeature(
    'vuetify',
    () => import(/* webpackChunkName: "vuetify" */ './vuetify'),
    ['mdi', ...['roboto', 'vuetify-css'].filter(name => !leftOut(name))],
    false,
    require.resolveWeak('./vuetify'),
);
// CSS only: Vuetify's CSS (main{M}.vuetify.css; MoveCssPlugin in webpack.config.js moves the
// CSS of the vuetify chunk into this chunk), fonts and icons
solara.registerFeature('vuetify-css', () => import(/* webpackChunkName: "vuetify-css" */ './vuetify-css'), [], true);
solara.registerFeature('mdi', () => import(/* webpackChunkName: "mdi" */ '@mdi/font/css/materialdesignicons.css'), [], true);
solara.registerFeature('material-icons', () => import(/* webpackChunkName: "material-icons" */ 'material-design-icons-iconfont/dist/material-design-icons.css'), [], true);
solara.registerFeature('roboto', () => import(/* webpackChunkName: "roboto" */ 'typeface-roboto'), [], true);

export { solara };

export { Vue };
