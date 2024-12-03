
import Vue from 'vue';
import Vuetify from 'vuetify';
import 'vuetify/dist/vuetify.min.css';
import { addCompiler } from '@mariobuikhuizen/vue-compiler-addon';

addCompiler(Vue);

Vue.use(Vuetify);

import * as solara from './solara';
export { solara };

export { Vue };
export { Vuetify };
