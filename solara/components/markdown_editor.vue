<template>
  <div>
    <div
      ref="editor"
      class="
        solara-milkdown solara-markdown
        rendered_html
        jp-RenderedHTMLCommon
      "
    ></div>
  </div>
</template>
<script>
module.exports = {
  mounted() {
    const version = "6.3.0";
    console.log(this);
    (async () => {
      console.log(this);
      const {
        Editor,
        nord,
        commonmark,
        rootCtx,
        defaultValueCtx,
        menu,
        listenerCtx,
        listener,
        ThemeGlobal,
        ThemeIcon,
        ThemeColor,
        ThemeSize,
        history,
      } = (
        await this.import([
          `${this.getCdn()}/@widgetti/solara-milkdown@${version}/dist/index.min.js`,
        ])
      )[0];

      const iconMapping = {
        h1: {
          label: "h1",
          icon: "",
        },
        h2: {
          label: "h2",
          icon: "",
        },
        h3: {
          label: "h3",
          icon: "",
        },
        loading: {
          label: "loading",
          icon: "",
        },
        quote: {
          label: "quote",
          icon: "mdi-format-quote-close",
        },
        code: {
          label: "code",
          icon: "mdi-code-braces",
        },
        table: {
          label: "table",
          icon: "mdi-table",
        },
        divider: {
          label: "divider",
          icon: "mdi-minus",
        },
        image: {
          label: "image",
          icon: "mdi-image",
        },
        brokenImage: {
          label: "broken image",
          icon: "",
        },
        bulletList: {
          label: "bullet list",
          icon: "mdi-format-list-bulleted",
        },
        orderedList: {
          label: "ordered list",
          icon: "mdi-format-list-numbered",
        },
        taskList: {
          label: "task list",
          icon: "",
        },
        bold: {
          label: "bold",
          icon: "mdi-format-bold",
        },
        italic: {
          label: "italic",
          icon: "mdi-format-italic",
        },
        inlineCode: {
          label: "inline code",
          icon: "mdi-code-braces-box",
        },
        strikeThrough: {
          label: "strike through",
          icon: "mdi-format-strikethrough",
        },
        link: {
          label: "link",
          icon: "mdi-link",
        },
        leftArrow: {
          label: "left arrow",
          icon: "chevron_left",
        },
        rightArrow: {
          label: "right arrow",
          icon: "",
        },
        upArrow: {
          label: "up arrow",
          icon: "",
        },
        downArrow: {
          label: "down arrow",
          icon: "mdi-menu-down",
        },
        alignLeft: {
          label: "align left",
          icon: "",
        },
        alignRight: {
          label: "align right",
          icon: "",
        },
        alignCenter: {
          label: "align center",
          icon: "",
        },
        delete: {
          label: "delete",
          icon: "",
        },
        select: {
          label: "select",
          icon: "mdi-select",
        },
        unchecked: {
          label: "unchecked",
          icon: "",
        },
        checked: {
          label: "checked",
          icon: "",
        },
        undo: {
          label: "undo",
          icon: "mdi-undo",
        },
        redo: {
          label: "redo",
          icon: "mdi-redo",
        },
        liftList: {
          label: "unindent",
          icon: "mdi-format-indent-decrease",
        },
        sinkList: {
          label: "indent",
          icon: "mdi-format-indent-increase",
        },
      };

      const extendedNord = nord.override((emotion, manager) => {
        // resets css styling
        manager.set(ThemeColor, ([key, opacity]) => {
          return null;
        });
        manager.set(ThemeGlobal, () => {});
        manager.set(ThemeSize, () => {});
        manager.set(ThemeIcon, (key) => {
          const target = iconMapping[key];
          if (!target) {
            return;
          }
          if (!target.icon) {
            console.log(key, "missing");
            target.icon = "mdi-alert-circle";
          }
          const { icon, label } = target;
          const span = document.createElement("span");
          span.className = `mdi v-icon ${icon}`;

          return {
            dom: span,
            label,
          };
        });
      });

      Editor.make()
        .config((ctx) => {
          ctx.set(rootCtx, this.$refs.editor);
          ctx.set(defaultValueCtx, this.value);
          ctx
            .get(listenerCtx)
            .markdownUpdated((ctx, markdown, prevMarkdown) => {
              this.value = markdown;
            });
        })
        .use(extendedNord)
        .use(commonmark)
        .use(menu)
        .use(listener)
        .use(history)
        .create();
    })();
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
  },
};
</script>

<style id="solara-markdown-editor">
.solara-milkdown {
  position: relative; /* since the dropdown uses position absolute */
}

div.solara-milkdown {
  padding-right: 0px; /* just the top element, otherwise the menu is not full width. */
}

.solara-markdown strong {
  font-weight: bold;
}

/* Milkdown produces a p element in the li, while in the notebook that does not happen, by removing the bottom margin it looks the same.
   v6.3 puts another div in it it seems, therefore we have the second rule
*/
.solara-markdown li > p,
.solara-markdown li > .list-item_body > p {
  margin: 0;
}

/* not sure why these get added, so we 'remove' them */
.solara-milkdown .list-item_label {
  display: none;
}

/* easiest way to remove the table button, which we do not support yet, only using the 'gfm' preset */
.solara-milkdown button[aria-label~="table"] {
  display: none;
}

/*  .jp-RenderedHTMLCommon blockquote was less specific than what vuetify did, so make this rule more specific */
.jp-RenderedHTMLCommon .blockquote {
  margin: 1em 2em;
  padding: 0 1em;
  border-left: 5px solid var(--jp-border-color2);
}

.solara-milkdown .milkdown-menu {
  border-color: var(--jp-content-font-color3);
}

.solara-milkdown button {
  color: var(--jp-content-font-color2);
}

.solara-milkdown .menu-selector-list,
.solara-milkdown .code-fence_selector-list {
  background-color: var(--jp-layout-color0);
}

.solara-milkdown .code-fence {
  background-color: var(--jp-layout-color2);
}

.solara-milkdown .code-fence_selector,
.solara-milkdown .image-container.empty {
  background-color: var(--jp-layout-color3);
  border: 0;
}

.solara-markdown .tooltip-input {
  background-color: var(--jp-layout-color0);
}

/* get classic notebook consistent */
.solara-milkdown .menu-selector-wrapper,
.solara-milkdown button {
  font-size: 12.25px;
}
.solara-milkdown .image-container .placeholder {
  font-size: 20px;
}

.solara-markdown ul {
  margin-block-start: 1em;
  margin-block-end: 1em;
  margin-inline-start: 0px;
  margin-inline-end: 0px;
  padding-inline-start: 40px;
}

/* classic notebook shows a blue border otherwise */
.solara-milkdown [contenteditable] {
  outline: 0px solid transparent;
}
</style>
