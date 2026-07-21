import * as Vue from 'vue';
import * as Vuetify from 'vuetify';
import 'vuetify/dist/vuetify.min.css';

import * as components from 'vuetify/components';
import * as labComponents from 'vuetify/labs/components';
import * as directives from 'vuetify/directives';

const dark = typeof globalThis.inDarkMode === 'function' && globalThis.inDarkMode();

const vuetifyPlugin = Vuetify.createVuetify({
    components: {
        ...components,
        ...labComponents,
    },
    directives,
    theme: globalThis.vuetifyThemes ? {
        defaultTheme: dark ? 'dark' : 'light',
        themes: globalThis.vuetifyThemes,
    } : undefined,
});


import * as solara from './solara';
export { solara };

export { Vue, Vuetify, vuetifyPlugin };
