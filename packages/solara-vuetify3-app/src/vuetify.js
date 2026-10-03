// feature "vuetify": the Vuetify JS and CSS
import * as Vue from 'vue';
import * as Vuetify from 'vuetify';
import 'vuetify/dist/vuetify.min.css';

import * as components from 'vuetify/components';
import * as labComponents from 'vuetify/labs/components';
import * as directives from 'vuetify/directives';
import colors from 'vuetify/util/colors';

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

// The theme colors of solara.lab.theme (ipyvuetify's ThemeColors widgets), as ipyvuetify's
// VuetifyView applies them. The widget manager calls this for each ThemeColorsModel only when
// this chunk loaded on first use into the shell without Vuetify: there no VuetifyView sets up
// the theme, because the root of the page is an ipyvue.Html.
function parseColor(value) {
    // e.g. "colors.teal" or "colors.teal.lighten2"
    let result = colors;
    value.split('.').slice(1).forEach(part => {
        result = result && result[part];
    });
    return typeof result === 'string' ? result : result && result.base;
}

function themeColors(model) {
    const result = {};
    Object.entries(model.attributes).forEach(([key, value]) => {
        if (key.startsWith('_') || ['accent', 'anchor', 'custom_theme_colors'].includes(key) || typeof value !== 'string') {
            return;
        }
        result[key.replace(/_/g, '-')] = value.startsWith('colors.') ? parseColor(value) : value;
    });
    return { ...result, ...(model.get('custom_theme_colors') || {}) };
}

function followThemeColors(model) {
    const apply = () => {
        const theme = vuetifyPlugin.theme.themes.value[model.get('_theme_name')];
        if (theme) {
            theme.colors = { ...(theme.colors || {}), ...themeColors(model) };
        }
    };
    apply();
    model.on('change', apply);
}

export { Vuetify, vuetifyPlugin, followThemeColors };
