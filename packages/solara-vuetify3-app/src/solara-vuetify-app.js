import * as Vue from 'vue';

import * as solara from './solara';

// The frontend features of this bundle, next to the ones of the widget manager.
// Vuetify (JS + CSS) is a chunk: a page without it uses a pure Vue shell.
solara.registerFeature(
    'vuetify',
    () => import(/* webpackChunkName: "vuetify" */ './vuetify'),
    ['mdi'],
    false,
    require.resolveWeak('./vuetify'),
);
// CSS only (fonts and icons)
solara.registerFeature('mdi', () => import(/* webpackChunkName: "mdi" */ '@mdi/font/css/materialdesignicons.css'), [], true);
solara.registerFeature('material-icons', () => import(/* webpackChunkName: "material-icons" */ 'material-design-icons-iconfont/dist/material-design-icons.css'), [], true);
solara.registerFeature('roboto', () => import(/* webpackChunkName: "roboto" */ 'typeface-roboto'), [], true);

export { solara };

export { Vue };
