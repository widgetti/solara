<template>
  <div>
    <div v-if="gridlayout_loaded" style="padding: 0px; width: 100%;">
       <grid-layout
            :layout.sync="grid_layout"
            :col-num="12"
            :row-height="30"
            :is-draggable="draggable"
            :is-resizable="resizable"
            :is-mirrored="false"
            :vertical-compact="true"
            :margin="[10, 10]"
            :use-css-transforms="true"
    >

        <grid-item v-for="item in grid_layout"
                   :x="item.x"
                   :y="item.y"
                   :w="item.w"
                   :h="item.h"
                   :i="item.i"
                   :key="item.i"
                   @resized="resizedEvent">
            <div v-if="!items[item.i]">
              placeholder: {{item.i}}
            </div>
            <div v-if="items[item.i]">
              <jupyter-widget :widget="items[item.i]" :key="'child_' + item.i"></jupyter-widget>
            </div>
        </grid-item>
    </grid-layout>

    </div>
  </div>
</template>

<script>
module.exports = {
    async created() {
      this.gridlayout_loaded = false

      define("vue", ['jupyter-vue'], jupyterVue => {
        jupyterVue.default = jupyterVue.Vue
        return jupyterVue
      });

      const {GridLayout, GridItem} = (await this.import(['https://cdn.jsdelivr.net/npm/@widgetti/vue-grid-layout@2.3.13-alpha.2/dist/vue-grid-layout.umd.js']))[0]
      this.$options.components['grid-item'] = GridItem;
      this.$options.components['grid-layout'] = GridLayout;
      this.gridlayout_loaded = true;
    },
    methods: {
        resizedEvent(i, newH, newW, newHPx, newWPx) {
          // this will cause bqplot to layout itself
          window.dispatchEvent(new Event('resize'));
        },
        import(deps) {
          return this.loadRequire()
              .then(() => new Promise((resolve, reject) => {
                requirejs(deps, (...modules) => resolve(modules));
              }));
        },
        loadRequire() {
          /* Needed in lab */
          if (window.requirejs) {
              console.log('require found');
              return Promise.resolve()
          }
          return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.6/require.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
          });
        }
    }
}
</script>

<style id="grid_layout">
.vue-grid-item > div {
  height: 100%;
}
</style>
