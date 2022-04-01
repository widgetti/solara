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
                    window.history.pushState(null, null, this.location)
                }
            }
        },
    }
</script>
