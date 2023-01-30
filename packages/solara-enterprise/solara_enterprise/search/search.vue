<template>
    <div>
        <v-menu v-model="search_open" offset-y>
            <template v-slot:activator="on">
                <v-text-field prepend-icon="mdi-magnify" v-model="query" return-object append-icon="" no-filter
                    clearable @click="onClick" hide-details class="d-none d-md-flex">
                </v-text-field>

            </template>
            <v-card class="solara-search-menu">
                <div v-if="failed">
                    <v-alert type="error">
                        Failed to load search index, maybe the server is still indexing.
                        <v-btn text @click="fetchData">Retry</v-btn>
                    </v-alert>
                </div>
                <v-list class="pa-3" :key="forceUpdateList" v-if="!failed">
                    <v-list-item v-for="item in items.slice(0, 20)" v-if="items" @click="onClickItem(item)">
                        <v-list-item-content class="solara-search-list-item">
                            <v-list-item-title>{{ item.title }}</v-list-item-title>
                            <v-list-item-subtitle>{{ item.location }}</v-list-item-subtitle>
                            <v-list-item-subtitle>{{ item.text }}</v-list-item-subtitle>
                        </v-list-item-content>
                    </v-list-item>
                    <v-list-item v-if="items.length > 20">
                        <v-list-item-content>
                            And {{ items.length - 20 }} more pages.
                        </v-list-item-content>

                    </v-list-item>
                    <v-list-item v-if="items.length == 0">
                        No search results found.
                    </v-list-item>
                </v-list>
            </v-card>
        </v-menu>
    </div>
</template>
<script>
module.exports = {
    created() {
        this.items = [];
    },
    async mounted() {
        window.search = this;
        await this.loadRequire();
        this.lunr = (await this.import([`${this.getCdn()}/lunr/lunr.js`]))[0];
        this.fetchData();
        window.search = this;

    },
    watch: {
        query(value) {
            this.search_open = true;
            this.search();
        },
        item(value) {
            solara.router.push(value.location);
            this.$nextTick(() => {
                // we cannot do this directly it seems
                // this.query = "";
            })
        },
    },
    methods: {
        async fetchData() {
            const url = `${window.solara.rootPath}/static/assets/search.json`
            let documents = [];
            try {
                documents = await (await fetch(url)).json();
                this.failed = false;
            } catch (e) {
                this.failed = true;
                return;
            }

            this.documents = {}
            documents.forEach((document) => {
                this.documents[document.location] = document;
            })
            this.idx = this.lunr(function () {
                this.ref('location')
                this.field('title')

                this.field('text')
                documents.forEach(function (doc) {
                    this.add(doc)
                }, this)
            })

        },
        onClickItem(item) {
            // console.log(item)
            this.item = item;
        },
        onClick() {
            this.search_open = true;
        },
        search() {
            if (this.idx) {
                const searchResult = this.idx.search(this.query || "");
                items = []
                searchResult.forEach((item) => {
                    items.push(this.documents[item.ref])
                })
                this.items = items;
                // items is not reactive, so use this proxy
                this.forceUpdateList += 1
            }
        },
        import(deps) {
            return this.loadRequire().then(
                () => {
                    if (window.jupyterVue) {
                        // in jupyterlab, we take Vue from ipyvue/jupyterVue
                        define("vue", [], () => window.jupyterVue.Vue);
                    } else {
                        define("vue", ['jupyter-vue'], jupyterVue => jupyterVue.Vue);
                    }
                    return new Promise((resolve, reject) => {
                        requirejs(deps, (...modules) => resolve(modules));
                    })
                }
            );
        },
        loadRequire() {
            /* Needed in lab */
            if (window.requirejs) {
                console.log('require found');
                return Promise.resolve()
            }
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = `${this.getCdn()}/requirejs@2.3.6/require.js`;
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        },
        getBaseUrl() {
            if (window.solara && window.solara.rootPath !== undefined) {
                return solara.rootPath + "/";
            }
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
            return (typeof solara_cdn !== "undefined" && solara_cdn) || `${this.getBaseUrl()}_solara/cdn`;
        },
    }
}
</script>
<style id="solara-search">
.solara-search-list-item {
    max-width: 400px;
}

.solara-search-menu {
    max-height: 80vh;
}
</style>
