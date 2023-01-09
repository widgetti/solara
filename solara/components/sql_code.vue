<template>
  <div>
    <v-subheader class="pl-0 query-input-label">{{ label }}</v-subheader>
    <div ref="cm" class="solara-sql-code" :style="`height: ${height};`"></div>
    <div>Use <kbd>Ctrl</kbd>+<kbd>Space</kbd> for auto-complete</div>
  </div>
</template>
<script>
  module.exports = {
    async mounted() {
      const cmVersion = '5.65.3';

      if (!document.getElementById('codemirror-hint.css')) {
        const link = document.createElement('link');
        link.href = `${this.getCdn()}/codemirror@${cmVersion}/addon/hint/show-hint.css`;
        link.type = "text/css";
        link.rel = "stylesheet";
        link.id="codemirror-hint.css";
        document.head.appendChild(link);
      }

      await this.loadRequire();

      requirejs.config({paths:{
          codemirror: `${this.getCdn()}/codemirror@${cmVersion}`
      }});

      requirejs(["codemirror/lib/codemirror", "codemirror/mode/sql/sql", "codemirror/addon/hint/show-hint", "codemirror/addon/hint/sql-hint"],
          (cm) => {
            this.myCodeMirror = cm(this.$refs.cm, {
              value: this.query || '',
              mode: "text/x-sql",
              extraKeys: {"Ctrl-Space": "autocomplete"},
              hint: cm.hint.sql,
              hintOptions: {
                tables: this.tables
              },
              lineNumbers: true,
              gutter: true,
            });
            this.myCodeMirror.on('change', (cm, changeObj) => this.query=cm.getValue())
          });
    },
    watch: {
      query(value) {
        if (this.myCodeMirror.getValue() !== value) {
          this.myCodeMirror.setValue(value)
        }
      },
      tables(value) {
        if (this.myCodeMirror) {
          this.myCodeMirror.options.hintOptions.tables = value;
        }
      }
    },
    methods: {
      import(deps) {
        return this.loadRequire().then(
          () => {
            if(window.jupyterVue) {
              // in jupyterlab, we take Vue from ipyvue/jupyterVue
              define("vue", [], () => window.jupyterVue.Vue);
            } else {
              define("vue", ['jupyter-vue'], jupyterVue => jupyterVue.Vue);
            }
            return new Promise((resolve, reject) => {
              requirejs(deps, (...modules) => resolve(modules));
            })
          }
        );
      },
      loadRequire() {
        /* Needed in lab */
        if (window.requirejs) {
            console.log('require found');
            return Promise.resolve()
        }
        return new Promise((resolve, reject) => {
          const script = document.createElement('script');
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
          return document.baseURI;
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
        return (typeof solara_cdn !== "undefined" && solara_cdn) || `${this.getBaseUrl()}_solara/cdn`;
      },
    }
  }
</script>
<style id="solara-sql-code">
.solara-sql-code {
  border: 1px solid gray;
}

ul.CodeMirror-hints.default {
  z-index: 10000;
}

.solara-sql-code .CodeMirror.cm-s-default {
  height: 100%
}

.v-subheader.query-input-label {
  font-size: 12px;
  height: unset;
}
</style>
