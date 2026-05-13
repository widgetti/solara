<template>
  <div v-if="!loaded">
    <div class="loading-text"></div>
  </div>
</template>

<script>
module.exports = {
  mounted() {
    const check = () => {
      if (window.Bokeh) {
        this.loaded = true;
        return;
      }
      setTimeout(check, 100);
    };
    check();
  },
};
</script>

<style>
.loading-text {
  margin-top: 10px;
  font-size: 16px;
}
</style>
