<template>
    <v-btn
        icon
        @click="countClicks"
        >
        <v-icon
            :color="theme_effective ? 'primary' : null">
            {{ this.clicks === 1 ? this.on_icon : this.clicks === 2 ? this.off_icon : this.auto_icon }}
        </v-icon>
    </v-btn>
</template>
<script>
module.exports = {
    mounted() {
        if ( this.theme_effective === false ) {
            this.clicks = 2;
        } else if ( this.theme_effective === null ) {
            this.clicks = 3;
        }
    },
    methods: {
        countClicks() {
            const lim = this.enable_auto ? 3 : 2;
            if ( this.clicks < lim ) {
                this.clicks++;
            } else {
                this.clicks = 1;
            }

            if ( this.clicks === 3 ) {
                this.theme_effective = null;
            } else if ( this.clicks === 2 ) {
                this.theme_effective = false;
            } else {
                this.theme_effective = true;
            }
            if ( window.solara ) {theme.variant = this.stringifyTheme();}
            this.setTheme();
            if ( window.solara ) {localStorage.setItem('theme.variant', JSON.stringify(theme.variant));}
            this.sync_themes(this.theme_effective);
        },
        stringifyTheme() {
            return this.theme_effective === true ? 'dark' : this.theme_effective === false ? 'light' : 'auto';
        },
        setTheme() {
            if ( window.solara && this.theme_effective === null ) {
                this.$vuetify.theme.dark = this.prefersDarkScheme();
                return;
            }
            this.$vuetify.theme.dark = this.theme_effective;
        },
        prefersDarkScheme() {
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
        },
    },
    data: () => ({
        clicks: 1,
    })
}
</script>
