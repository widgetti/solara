<template>
    <div id="docsearch">
    </div>
</template>

<script>
module.exports = {
    mounted() {
        // like open in new window
        solaraAlgoliaInit({appId: this.app_id, apiKey: this.api_key, indexName: this.index_name, debug: this.debug})
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
