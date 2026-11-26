<template>
  <div ref="editor" class="solara-code-editor" :style="`height: ${height};`"></div>
</template>
<script>
  module.exports = {
    async mounted() {
      await this.loadRequire();
      await this.loadEditor();
    },
    watch: {
      value(value) {
        if (this.view && this.view.state.doc.toString() !== value) {
          this.view.dispatch({
            changes: { from: 0, to: this.view.state.doc.length, insert: value || '' },
          });
        }
      },
      language() { this.reconfigure(); },
      theme() { this.reconfigure(); },
      read_only() { this.reconfigure(); },
      line_numbers() { this.reconfigure(); },
      tab_size() { this.reconfigure(); },
    },
    methods: {
      async loadEditor() {
        const deps = [
          '@codemirror/state',
          '@codemirror/view',
          '@codemirror/basic-setup',
          '@codemirror/language',
          '@codemirror/lang-python',
          '@codemirror/lang-javascript',
          '@codemirror/lang-json',
          '@codemirror/lang-markdown',
          '@codemirror/lang-sql',
        ];
        const modules = await this.import(deps);
        this.cm = {
          State: modules[0],
          View: modules[1],
          basicSetup: modules[2],
          language: modules[3],
          python: modules[4],
          javascript: modules[5],
          json: modules[6],
          markdown: modules[7],
          sql: modules[8],
        };
        this.makeView();
      },
      makeView() {
        const { EditorState, Compartment } = this.cm.State;
        const { EditorView } = this.cm.View;
        this.languageCompartment = this.languageCompartment || new Compartment();
        this.themeCompartment = this.themeCompartment || new Compartment();
        this.readOnlyCompartment = this.readOnlyCompartment || new Compartment();
        this.lineNumbersCompartment = this.lineNumbersCompartment || new Compartment();
        this.tabSizeCompartment = this.tabSizeCompartment || new Compartment();
        const extensions = [
          this.cm.basicSetup.basicSetup,
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              const next = update.state.doc.toString();
              if (next !== this.value) this.value = next;
            }
          }),
          this.languageCompartment.of(this.languageExtension()),
          this.themeCompartment.of([]),
          this.readOnlyCompartment.of(EditorState.readOnly.of(!!this.read_only)),
          this.lineNumbersCompartment.of(this.lineNumbersExtension()),
          this.tabSizeCompartment.of(EditorState.tabSize.of(this.tab_size || 4)),
          EditorView.lineWrapping,
        ];
        this.view = new EditorView({ state: EditorState.create({ doc: this.value || '', extensions }), parent: this.$refs.editor });
      },
      languageExtension() {
        switch ((this.language || 'python').toLowerCase()) {
          case 'javascript': case 'js': return this.cm.javascript.javascript();
          case 'json': return this.cm.json.json();
          case 'markdown': case 'md': return this.cm.markdown.markdown();
          case 'sql': return this.cm.sql.sql();
          default: return this.cm.python.python();
        }
      },
      lineNumbersExtension() { return this.line_numbers ? this.cm.View.lineNumbers() : []; },
      reconfigure() {
        if (!this.view) return;
        const effects = [
          this.languageCompartment.reconfigure(this.languageExtension()),
          this.themeCompartment.reconfigure([]),
          this.readOnlyCompartment.reconfigure(this.cm.State.EditorState.readOnly.of(!!this.read_only)),
          this.lineNumbersCompartment.reconfigure(this.lineNumbersExtension()),
          this.tabSizeCompartment.reconfigure(this.cm.State.EditorState.tabSize.of(this.tab_size || 4)),
        ];
        this.view.dispatch({ effects });
      },
      import(deps) {
        return this.loadRequire().then(() => {
          if (window.jupyterVue) define('vue', [], () => window.jupyterVue.Vue);
          else define('vue', ['jupyter-vue'], jupyterVue => jupyterVue.Vue);
          return new Promise((resolve, reject) => requirejs(deps, (...modules) => resolve(modules)));
        });
      },
      loadRequire() {
        if (window.requirejs) return Promise.resolve();
        return new Promise((resolve, reject) => {
          const script = document.createElement('script');
          script.src = `${this.getCdn()}/requirejs@2.3.6/require.js`;
          script.onload = resolve;
          script.onerror = reject;
          document.head.appendChild(script);
        });
      },
      getJupyterBaseUrl() {
        if (document.getElementsByTagName('base').length) return document.baseURI;
        const labConfigData = document.getElementById('jupyter-config-data');
        if (labConfigData) return JSON.parse(labConfigData.textContent).baseUrl;
        let base = document.body.dataset.baseUrl || document.baseURI;
        if (!base.endsWith('/')) base += '/';
        return base;
      },
      getCdn() { return this.cdn || (window.solara ? window.solara.cdn : `${this.getJupyterBaseUrl()}_solara/cdn`); },
    },
  };
</script>
<style>
.solara-code-editor { border: 1px solid var(--jp-border-color2, #ccc); overflow: hidden; }
</style>
