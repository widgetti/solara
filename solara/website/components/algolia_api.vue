<template>
    <v-menu
        v-model="show_results"
        offset-y>
        <template v-slot:activator="{ on }">
                <v-text-field
                    v-model="query"
                    prepend-inner-icon="mdi-magnify"
                    hide-details
                    dense
                    :placeholder="mac ? '⌘K to search' : 'Ctrl+K to search'"
                    filled
                    outlined
                    clearable
                    ref="search"
                    style="flex-grow: 1; max-width: 650px;"
                    @click="show($event, on);"
                    @keyup.enter="hoverItem === null ? item = 0 : item = hoverItem"
                    @keyup.esc="close();"
                    @keyup.down="hoverItem = hoverItem == null ? 0 : Math.min(hoverItem + 1, results.hits.length - 1, 9)"
                    @keyup.up="hoverItem = hoverItem == null ? 9 : Math.max(hoverItem - 1, 0)"
                    @focus="selectText();"
                    class="algolia"
                ></v-text-field>
        </template>
        <v-list v-if="results != null && results.length == 0">
            <v-list-item>
                <v-list-item-content>
                    {{this.query == "" ? "Start Typing to Search" : "No search results found."}}
                </v-list-item-content>
            </v-list-item>
        </v-list>
        <v-list v-else :style="{width: menuWidth + 'px'}">
            <v-list-item-group v-model="item">
                <v-list-item v-for="(element, index) in this.results.hits" :key="element['url']" :input-value="index === hoverItem">
                    <v-list-item-content>
                        <v-list-item-title>
                            {{ element.hierarchy.lvl1 }}
                        </v-list-item-title>
                        <v-list-item-subtitle v-if="element.hierarchy.lvl2 !== null">
                            {{ element.hierarchy.lvl2 }}
                        </v-list-item-subtitle>
                        <v-list-item-subtitle v-html="getSnippet(element)"></v-list-item-subtitle>
                    </v-list-item-content>
                </v-list-item>
            </v-list-item-group>
            <v-list-item v-if="this.results.nbHits > 10">
                <v-list-item-content>
                    <v-list-item-title>And {{ this.results.nbHits - 10}} More...</v-list-item-title>
                </v-list-item-content>
            </v-list-item>
        </v-list>
    </v-menu>
</template>
<script>
const search = ref(null);
module.exports = {
    async mounted() {
        window.search = this;
        await this.loadRequire();
        this.algoliasearch = (await this.import([`https://cdn.jsdelivr.net/npm/algoliasearch@4.20.0/dist/algoliasearch-lite.umd.js`]))[0];
        this.initSearch();
        window.search = this;
        this.updateMenuWidth();
        window.addEventListener('resize', this.updateMenuWidth);
    },
    watch: {
        query ( value ) {
            this.show_results = true;
            this.search();
        },
        item ( value ) {
            if ( value === null ) return;
            if ( this.results.hits != null && this.results.hits.length >= value ) {
                let url = this.results.hits[value].url;
                if (url.startsWith("https://solara.dev")) {
                    url = url.slice(18);
                }
                solara.router.push( url );
                this.close();
                // reset the search
                this.item = null;
                this.hoverItem = null;
            }
        },
    },
    methods: {
        show( e, on ) {
            this.show_results = false;
            this.$nextTick( () => {
                on.click( e )
            } );
        },
        close() {
            this.show_results = false;
            this.$refs.search.blur();
        },
        initSearch() {
            this.client = this.algoliasearch( '9KW9L7O5EQ', '647ca12ba642437cc40c2adee4a78d08' );
            this.index = this.client.initIndex( 'solara' );
            this.mac = window.navigator.userAgent.indexOf("Mac") != -1;
            document.addEventListener( 'keydown', ( e ) => {

                if (this.mac) {
                    if ( this.$refs.search && e.metaKey && e.key === 'k' ) {
                        this.$refs.search.focus();
                    }
                }else{
                    if ( this.$refs.search && e.ctrlKey && e.key === 'k' ) {
                        this.$refs.search.focus();
                    }
                }
            });
        },
        async search() {
            results = await this.index.search( this.query, { hitsPerPage: 10 } );
            if (results) {
                this.results = results;
            }else{
                this.$set(this.results, []);
            }
        },
        selectText() {
            this.$refs.search.$refs.input.select();
        },
        getSnippet( element ) {
            if (element.type == "content") {
                return element._highlightResult.content.value;
            }
            let snippet = element._highlightResult.hierarchy[element.type].value;
            if (snippet.matchLevel === "none" ) {
                snippet = element._highlightResult.hierarchy["lvl" + parseInt(element.type[3] - 1)].value
            }
            return snippet;
        },
        updateMenuWidth() {
            // Ensure the element is rendered and has dimensions
            this.$nextTick(() => {
                const activator = this.$refs.search;
                if (activator && activator.$el) {
                // Update the menuWidth with the activator's width
                this.menuWidth = activator.$el.offsetWidth;
                }
            });
        },
        import(dependencies) {
            return this.loadRequire().then(
                () => {
                    if (window.jupyterVue) {
                        // in jupyterlab, we take Vue from ipyvue/jupyterVue
                        define("vue", [], () => window.jupyterVue.Vue);
                    } else {
                        define("vue", ['jupyter-vue'], jupyterVue => jupyterVue.Vue);
                    }
                    return new Promise((resolve, reject) => {
                        requirejs(dependencies, (...modules) => resolve(modules));
                    })
                }
            );
        },
        loadRequire() {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = `${this.getCdn()}/requirejs@2.3.6/require.js`;
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        },
        getJupyterBaseUrl() {
            // if base url is set, we use ./ for relative paths compared to the base url
            if (document.getElementsByTagName("base").length) {
                return document.baseURI;
            }
            const labConfigData = document.getElementById('jupyter-config-data');
            if (labConfigData) {
                /* lab and Voila */
                return JSON.parse(labConfigData.textContent).baseUrl;
            }
            let base = document.body.dataset.baseUrl || document.baseURI;
            if (!base.endsWith('/')) {
                base += '/';
            }
            return base
        },
        getCdn() {
            return window.solara ? window.solara.cdn : `${this.getJupyterBaseUrl()}_solara/cdn`;
        },
    },
    data(){
        return {
            query: '',
            results: [],
            item: null,
            hoverItem: null,
            show_results: false,
            mac: false,
            menuWidth: 0,
        }
    },
}
</script>
