<template>
  <div>
    <div ref="echarts" class="solara-echarts" v-bind="attributes"></div>
  </div>
</template>
<script>
module.exports = {
  mounted() {
    const version = "5.4.0";
    (async () => {
      const echarts = (
        await this.import([`${this.getCdn()}/echarts@${version}/dist/echarts.js`])
      )[0];
      this.echarts = echarts;
      this.create();
    })();
  },
  watch: {
    option() {
      // notMerge, otherwise we're left with axes etc
      // see https://echarts.apache.org/en/api.html#echartsInstance.setOption
      this.chart.setOption(this.option, true);
    },
  },
  methods: {
    create() {
      this.chart = this.echarts.init(this.$refs.echarts);
      console.log(this.maps);
      Object.keys(this.maps).forEach((mapName) => {
        console.log(mapName);
        this.echarts.registerMap(mapName, this.maps[mapName]);
      });

      this.chart.setOption(this.option, true);
      const eventProps = [
        "componentType",
        "seriesType",
        "seriesIndex",
        "seriesName",
        "name",
        "dataIndex",
        "data",
        "dataType",
        "value",
        "color",
      ];
      this.chart.on("click", (fullEvent) => {
        const eventData = {};
        eventProps.forEach((prop) => {
          eventData[prop] = fullEvent[prop];
        });
        this.on_click(eventData);
      });
      this.chart.on("mouseover", (fullEvent) => {
        const eventData = {};
        eventProps.forEach((prop) => {
          eventData[prop] = fullEvent[prop];
        });
        if (this.on_mouseover_enabled) this.on_mouseover(eventData);
      });
      this.chart.on("mouseout", (fullEvent) => {
        const eventData = {};
        eventProps.forEach((prop) => {
          eventData[prop] = fullEvent[prop];
        });
        if (this.on_mouseout_enabled) this.on_mouseout(eventData);
      });
    },
    import(deps) {
      return this.loadRequire().then(() => {
        if (window.jupyterVue) {
          // in jupyterlab, we take Vue from ipyvue/jupyterVue
          define("vue", [], () => window.jupyterVue.Vue);
        } else {
          define("vue", ["jupyter-vue"], (jupyterVue) => jupyterVue.Vue);
        }
        return new Promise((resolve, reject) => {
          requirejs(deps, (...modules) => resolve(modules));
        });
      });
    },
    loadRequire() {
      /* Needed in lab */
      if (window.requirejs) {
        console.log("require found");
        return Promise.resolve();
      }
      return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = `${this.getCdn()}/requirejs@2.3.6/require.js`;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    },
    getBaseUrl() {
      if (window.solara && window.solara.rootPath !== undefined) {
        return solara.rootPath + "/";
      }
      // if base url is set, we use ./ for relative paths compared to the base url
      if (document.getElementsByTagName("base").length) {
        return "./";
      }
      const labConfigData = document.getElementById("jupyter-config-data");
      if (labConfigData) {
        /* lab and Voila */
        return JSON.parse(labConfigData.textContent).baseUrl;
      }
      let base = document.body.dataset.baseUrl || document.baseURI;
      if (!base.endsWith("/")) {
        base += "/";
      }
      return base;
    },
    getCdn() {
      return (
        (typeof solara_cdn !== "undefined" && solara_cdn) ||
        `${this.getBaseUrl()}_solara/cdn`
      );
    },
  },
};
</script>

<style id="solara-markdown-editor">
.solara-echarts {
}
</style>
