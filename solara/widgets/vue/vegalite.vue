<template>
    <div>
        <div ref="plotElement"></div>
    </div>
</template>
<script>
module.exports = {
    created() {
        requirejs.undef("vega")
        requirejs.undef("vega-lite")
        requirejs.undef("vega-embed")
        require.config({
            map: {
                '*': {
                    'vega': `${this.getCdn()}/vega@5.21.0`,
                    'vega-lite': `${this.getCdn()}/vega-lite@5.2.0`,
                    'vega-embed': `${this.getCdn()}/vega-embed@6.20.2`,
                }
            }
        })
        // pre load
        require(['vega', 'vega-lite', 'vega-embed'], () => {
            console.log('yeah')
        })
        this.do_plot_debounced = _.debounce(() => this.do_plot(), 100)
    },
    mounted() {
        this.do_plot_debounced();
    },
    watch: {
        spec() {
            this.do_plot_debounced();
        },
        listen_to_click() {
            this.do_plot_debounced();
        }
    },
    methods: {
        do_plot() {
            require(['vega', 'vega-lite', 'vega-embed'], (vega, vl, vegaEmbed) => {
                (async () => {
                    const { view } = await vegaEmbed(this.$refs.plotElement, this.spec);
                    // events https://github.com/vega/vega-view#event-handling
                    console.log(view)
                    if (this.listen_to_click) {
                        view.addEventListener('click', (event, item) => {
                            console.log(item, event)
                            if (item && item.datum) {
                                this.altair_click(item.datum);
                            } else {
                                this.altair_click(null)
                            }
                        })
                    }
                    if (this.listen_to_hover) {
                        view.addEventListener('mouseover', (event, item) => {
                            // console.log(item)
                            if (item && item.datum) {
                                this.altair_hover(item.datum);
                            } else {
                                this.altair_hover(null)
                            }
                        })
                    }
                })();
            });
        },
        getBaseUrl() {
            if (window.solara && window.solara.rootPath !== undefined) {
                return solara.rootPath + "/";
            }
            // if base url is set, we use ./ for relative paths compared to the base url
            if (document.getElementsByTagName("base").length) {
                return "./";
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
        }
    },
}
</script>
