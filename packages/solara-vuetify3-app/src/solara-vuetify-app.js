import * as Vue from 'vue';

import * as solara from './solara';

// The frontend features of this bundle, next to the ones of the widget manager.
// Vuetify (JS + CSS) is a chunk: a page without it uses a pure Vue shell.
// Vuetify's icons use mdi and its typography uses Roboto, so a lazy Vuetify loads both
// (into their CSS slots, the place of a preloaded link). An app with its own font leaves
// Roboto out with "-roboto" in --frontend: the page's normalized spec, where the last
// "+roboto" or "-roboto" wins (as in solara/server/frontend.py).
function leftOut(name) {
    const spec = (window.solaraFrontend && window.solaraFrontend.spec) || '';
    const tokens = spec.split(',');
    return tokens.lastIndexOf('-' + name) > tokens.lastIndexOf('+' + name);
}
solara.registerFeature(
    'vuetify',
    () => import(/* webpackChunkName: "vuetify" */ './vuetify'),
    leftOut('roboto') ? ['mdi'] : ['mdi', 'roboto'],
    false,
    require.resolveWeak('./vuetify'),
);
// CSS only (fonts and icons)
solara.registerFeature('mdi', () => import(/* webpackChunkName: "mdi" */ '@mdi/font/css/materialdesignicons.css'), [], true);
solara.registerFeature('material-icons', () => import(/* webpackChunkName: "material-icons" */ 'material-design-icons-iconfont/dist/material-design-icons.css'), [], true);
solara.registerFeature('roboto', () => import(/* webpackChunkName: "roboto" */ 'typeface-roboto'), [], true);

export { solara };

export { Vue };
