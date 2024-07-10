<template>
    <div>This component should call back to Python</div>
</template>
<script>
module.exports = {
    mounted() {
        console.log("mounted")
        pywebview.api.test("Test passes!")
    }
}
</script>
