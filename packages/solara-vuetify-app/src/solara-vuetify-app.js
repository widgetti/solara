
import { Vue, Vuetify } from 'jupyter-vuetify';
import 'jupyter-vuetify/dist/jupyter-vuetify.min.css';
import { addCompiler } from '@mariobuikhuizen/vue-compiler-addon';

addCompiler(Vue);

Vue.use(Vuetify);

import * as solara from './solara';
export { solara };

export { Vue };
export { Vuetify };
