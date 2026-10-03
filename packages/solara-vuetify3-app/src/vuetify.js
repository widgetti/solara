// feature "vuetify": the Vuetify JS and CSS
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

// the page and jupyter-vuetify's nodeps.js use these globals (they were exports of the core bundle)
if (typeof window !== 'undefined') {
    window.Vuetify = Vuetify;
    window.vuetifyPlugin = vuetifyPlugin;
    // Loaded lazily into a running pure Vue shell (vuetify feature off): install it on the
    // shell app. When preloaded, this runs before the page creates its app, which then
    // calls .use(vuetifyPlugin) itself.
    const shell = window.app;
    // mount() returns the root component instance, its app is in appContext
    const shellApp = shell && (shell.$ && shell.$.appContext ? shell.$.appContext.app : (typeof shell.use === 'function' ? shell : null));
    if (shellApp && shellApp.version === Vue.version) {
        shellApp.use(vuetifyPlugin);
    }
}

export { Vuetify, vuetifyPlugin };
