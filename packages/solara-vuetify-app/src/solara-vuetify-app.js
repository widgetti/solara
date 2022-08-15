import '@mdi/font/css/materialdesignicons.css';
import 'material-design-icons-iconfont/dist/material-design-icons.css';
import 'typeface-roboto';

import { addCompiler } from '@mariobuikhuizen/vue-compiler-addon';
import Vue from 'vue';
import Vuetify from 'vuetify';
import 'vuetify/dist/vuetify.min.css';

addCompiler(Vue);

Vue.use(Vuetify);

// import './solara'
// export * as solara from 'solara';
import * as solara from './solara';
export {solara};

export { Vue };
export { Vuetify };
