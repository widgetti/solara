<template>
    <div>If you see this, it is all working. The Qt app should automatically close after a second.</div>
</template>
<script>
module.exports = {
    mounted() {
        console.log("mounted")
        setTimeout(() => {
            this.rendered()
        }, 1000)
    }
}
</script>
