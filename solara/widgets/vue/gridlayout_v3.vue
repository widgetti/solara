<template>
  <div>
    <div v-if="gridlayout_loaded" style="padding: 0px; width: 100%;">
       <!-- a plain <grid-layout> tag is resolved before the v-if, when the
            component is not registered yet, which makes Vue 3 warn -->
       <component :is="'grid-layout'"
            v-model:layout="grid_layout"
            :col-num="col_num"
            :row-height="row_height"
            :is-draggable="draggable"
            :is-resizable="resizable"
            :is-mirrored="false"
            :vertical-compact="true"
            :margin="[10, 10]"
            :use-css-transforms="true"
            @layout-updated="onLayoutUpdated"
    >

        <component :is="'grid-item'" v-for="item in grid_layout"
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
        </component>
    </component>

    </div>
  </div>
</template>

<script>
module.exports = {
    async created() {
      this.gridlayout_loaded = false

      // @widgetti/vue-grid-layout is a Vue 2 build: under Vue 3 it throws
      // "GlobalVue.use is not a function" and the grid never shows.
      // grid-layout-plus is its Vue 3 port, with the same props and events.
      // Its ES module build only imports "vue", which ipyvue maps in its
      // import map. ipyvue runs this script as a blob module, which cannot
      // resolve a relative url, so we make the url absolute.
      const url = new URL(`${this.getCdn()}/grid-layout-plus@1.1.1/dist/grid-layout-plus.mjs`, document.baseURI).href;
      const {GridLayout, GridItem} = await import(url);
      this.$options.components['grid-item'] = GridItem;
      this.$options.components['grid-layout'] = GridLayout;
      this.gridlayout_loaded = true;
    },
    methods: {
        resizedEvent(i, newH, newW, newHPx, newWPx) {
          // this will cause bqplot to layout itself
          window.dispatchEvent(new Event('resize'));
        },
        onLayoutUpdated(layout) {
          this.layout_updated(layout);
        },
        getJupyterBaseUrl() {
          if (document.getElementsByTagName("base").length) {
            return "./";
          }
          const labConfigData = document.getElementById('jupyter-config-data');
          if(labConfigData) {
            /* lab and Voila */
            return JSON.parse(labConfigData.textContent).baseUrl;
          }
          let base = document.body.dataset.baseUrl || document.baseURI;
          if(!base.endsWith('/')) {
            base += '/';
          }
          return base
        },
        getCdn() {
          return this.cdn || (window.solara ? window.solara.cdn : `${this.getJupyterBaseUrl()}_solara/cdn`);
        },
    }
}
</script>

<style id="grid_layout">
.vgl-item > div {
  height: 100%;
}
</style>
