<template>
    <div id="docsearch">
    </div>
</template>

<script>
module.exports = {
    mounted() {
        // like open in new window
        const otherClick = (event) => event.button === 1 || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey
        docsearch({
            container: '#docsearch',
            appId: this.app_id,
            apiKey: this.api_key,
            indexName: this.index_name,
            debug: this.debug,
            hitComponent: ({ hit, children }) => {
                // react without the React library
                return {
                    type: 'a',
                    constructor: undefined,
                    __v: 1,
                    props: {
                        href: hit.url,
                        children,
                        onClick: (event) => {
                            if (otherClick(event)) { return }
                            event.preventDefault()
                            let url = hit.url;
                            if (url.startsWith('https://solara.dev')) {
                                url = url.substring(18);
                            }
                            solara.router.push(url)
                        }
                    }
                }
            },

            navigator: {
                navigate({ itemUrl }) {
                    if (itemUrl.startsWith('https://solara.dev')) {
                        itemUrl = itemUrl.substring(18);
                    }
                    solara.router.push(itemUrl);
                },
            },
        });
    }
}
</script>

<style id="algolia">
.DocSearch-Button {
    background-color: rgb(255, 238, 197);
    color: #182026;
}

.DocSearch-Button:hover {
    background-color: rgb(255, 247, 227);
}
</style>
