import * as Vue from 'vue';

import * as solara from './solara';

// The frontend features of this bundle, next to the ones of the widget manager.
// Vuetify (JS) is a chunk that the page always preloads (the page shell is made of Vuetify).
// Its CSS is the feature vuetify-css.
solara.registerFeature(
    'vuetify',
    () => import(/* webpackChunkName: "vuetify" */ './vuetify'),
    [],
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
