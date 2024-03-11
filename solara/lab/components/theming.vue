<template>
    <v-btn
        icon
        @click="countClicks"
        >
        <v-icon>
            {{ this.clicks === 1 ? this.on_icon : this.clicks === 2 ? this.off_icon : this.auto_icon }}
        </v-icon>
    </v-btn>
</template>
<script>
module.exports = {
    mounted() {
        if (window.solara) {
            if (localStorage.getItem(':solara:theme.variant')) {
                this.theme_dark = this.initTheme();
            }
        }

        if ( this.theme_dark === false ) {
            this.clicks = 2;
        } else if ( this.theme_dark === null ) {
            this.clicks = 3;
        }
        this.lim = this.enable_auto ? 3 : 2;
    },
    methods: {
        countClicks() {
            if ( this.clicks < this.lim ) {
                this.clicks++;
            } else {
                this.clicks = 1;
            }
            this.theme_dark = this.get_theme_bool( this.clicks );
        },
        get_theme_bool( clicks ) {
            if ( clicks === 3 ) {
                return null;
            } else if ( clicks === 2 ) {
                return false;
            } else {
                return true;
            }
        },
        stringifyTheme() {
            return this.theme_dark === true ? 'dark' : this.theme_dark === false ? 'light' : 'auto';
        },
        initTheme() {
            storedTheme = JSON.parse(localStorage.getItem(':solara:theme.variant'));
            return storedTheme === 'dark' ? true : storedTheme === 'light' ? false : null;
        },
        setTheme() {
            if ( window.solara && this.theme_dark === null ) {
                this.$vuetify.theme.dark = this.prefersDarkScheme();
                return;
            }
            this.$vuetify.theme.dark = this.theme_dark;
        },
        prefersDarkScheme() {
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
        },
    },
    watch: {
        clicks (val) {
            if ( window.solara ) {theme.variant = this.stringifyTheme();}
            this.setTheme();
            if ( window.solara ) {localStorage.setItem(':solara:theme.variant', JSON.stringify(theme.variant));}
            this.sync_themes(this.theme_dark);
        },
    }
}
</script>
