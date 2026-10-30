
import Vue from 'vue';
import Vuetify from 'vuetify';
import { addCompiler } from '@mariobuikhuizen/vue-compiler-addon';

addCompiler(Vue);

Vue.use(Vuetify);

import * as solara from './solara';

// The frontend features of this bundle, next to the ones of the widget manager.
// Vuetify is in the core bundle on Vue 2: jupyter-vuetify's nodeps.js reads the app's vuetify.
solara.provideFeature('vuetify', { Vuetify });
// Vuetify's CSS is a CSS-only feature (main{M}.vuetify.css), so an app can ship its own: the page always preloads it
// on Vue 2, before the core CSS (its place when it was part of main{M}.css), unless its --frontend says -vuetify-css
solara.registerFeature('vuetify-css', () => import(/* webpackChunkName: "vuetify-css" */ 'vuetify/dist/vuetify.min.css'), [], true);
// CSS only (fonts and icons); Vuetify needs mdi, so the page always preloads it on Vue 2, and roboto unless the
// page's --frontend says -roboto
solara.registerFeature('mdi', () => import(/* webpackChunkName: "mdi" */ '@mdi/font/css/materialdesignicons.css'), [], true);
solara.registerFeature('material-icons', () => import(/* webpackChunkName: "material-icons" */ 'material-design-icons-iconfont/dist/material-design-icons.css'), [], true);
solara.registerFeature('roboto', () => import(/* webpackChunkName: "roboto" */ 'typeface-roboto'), [], true);

export { solara };

export { Vue };
export { Vuetify };
