<template>
</template>
​
<script>
    modules.export = {
        created() {
            this.location = window.location.pathname
            window.addEventListener('popstate', (lala) => {
                // console.log('pop state!', lala, window.location.pathname )
                this.location = window.location.pathname
            });
        },
        watch: {
            location() {
                // console.log('changed', this.location)
                // if we use the back navigation, this watch will trigger,
                // but we don't want to push the history
                // otherwise we cannot go forward
                if(window.location.pathname != this.location) {
                    // we respect possible different bases, like when behind a proxy. e.g.
                    // <base href="https://myserver.com/someuser/project/a/">
                    // we assume location is absolute, so we remove the trailing /
                    window.history.pushState(null, null, document.baseURI.slice(0, -1) + this.location)
                }
            }
        },
    }
</script>
