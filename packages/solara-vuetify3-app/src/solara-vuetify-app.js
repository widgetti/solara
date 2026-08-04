import * as Vue from 'vue';
import * as Vuetify from 'vuetify';
import 'vuetify/dist/vuetify.min.css';

import * as components from 'vuetify/components';
import * as labComponents from 'vuetify/labs/components';
import * as directives from 'vuetify/directives';

const rawThemes = typeof window !== 'undefined' ? window.vuetifyThemes || {} : {};
const themes = Object.fromEntries(
    Object.entries(rawThemes).map(([name, theme]) => [
        name,
        theme.colors ? theme : { dark: name === 'dark', colors: theme },
    ]),
);

const vuetifyPlugin = Vuetify.createVuetify({
    components: {
        ...components,
        ...labComponents,
    },
    directives,
    theme: {
        themes,
    },
});


import * as solara from './solara';
export { solara };

export { Vue, Vuetify, vuetifyPlugin };
