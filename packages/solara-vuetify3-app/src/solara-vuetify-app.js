import * as Vue from 'vue';
import * as Vuetify from 'vuetify';
import 'vuetify/dist/vuetify.min.css';

import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';

const vuetifyPlugin = Vuetify.createVuetify({
    components,
    directives,
});


import * as solara from './solara';
export { solara };

export { Vue, Vuetify, vuetifyPlugin };
