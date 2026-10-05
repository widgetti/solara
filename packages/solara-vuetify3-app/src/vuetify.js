// feature "vuetify": the Vuetify JS. Its CSS (this CSS import, and the CSS that Vuetify's components
// import) is the feature "vuetify-css": MoveCssPlugin (webpack.config.js) moves it to that chunk.
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
}

export { Vuetify, vuetifyPlugin };
