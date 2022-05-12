<template>
  <div>
    <v-subheader class="pl-0 query-input-label">{{ label }}</v-subheader>
    <div ref="cm" class="solara-sql-code" :style="`height: ${height};`"></div>
    <div>Use <kbd>Ctrl</kbd>+<kbd>Space</kbd> for auto-complete</div>
  </div>
</template>
<script>
  module.exports = {
    mounted() {
      const cmVersion = '5.65.3';

      if (!document.getElementById('codemirror-hint.css')) {
        const link = document.createElement('link');
        link.href = `https://cdnjs.cloudflare.com/ajax/libs/codemirror/${cmVersion}/addon/hint/show-hint.min.css`;
        link.type = "text/css";
        link.rel = "stylesheet";
        link.id="codemirror-hint.css";
        document.head.appendChild(link);
      }

      requirejs.config({paths:{
          codemirror: `https://cdnjs.cloudflare.com/ajax/libs/codemirror/${cmVersion}`,
          'codemirror/lib': `https://cdnjs.cloudflare.com/ajax/libs/codemirror/${cmVersion}`}
      });

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
