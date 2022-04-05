<template>
</template>
​
<script>
    modules.export = {
        created() {
            this.location = window.location.pathname
            window.addEventListener('popstate', (lala) => {
                // console.log('pop state!', lala, window.location.pathname )
                if(!window.location.href.startsWith(document.baseURI)) {
                    throw `window.location = ${window.location}, but it should start with the document.baseURI = ${document.baseURI}`;
                }
                const newLocation = "/" + window.location.href.slice(document.baseURI.length)
                this.location = newLocation;
            });
        },
        watch: {
            location() {
                // console.log('changed', this.location)
                // if we use the back navigation, this watch will trigger,
                // but we don't want to push the history
                // otherwise we cannot go forward
                if(!window.location.href.startsWith(document.baseURI)) {
                    throw `window.location = ${window.location}, but it should start with the document.baseURI = ${document.baseURI}`;
                }
                const oldLocation = "/" + window.location.href.slice(document.baseURI.length)
                // console.log('location changed', oldLocation, this.location)
                if(oldLocation != this.location) {
                    // we prepend with "." to make it work behind a proxy. e.g.
                    // <base href="https://myserver.com/someuser/project/a/">
                    window.history.pushState(null, null, "." + this.location)
                }
            }
        },
    }
</script>
