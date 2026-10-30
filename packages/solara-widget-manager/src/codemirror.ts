// Stub for @jupyterlab/codemirror. The app bundles alias the '@jupyterlab/codemirror' import of
// @jupyterlab/rendermime (its markdown renderer) to this module, so CodeMirror is not in the core
// bundle. The markdown renderer reads the theme name, and highlights code blocks with Mode.ensure
// and Mode.run. CodeMirror loads (as the "codemirror" chunk) on the first code block with a language.
type ModeNamespace = typeof import('@jupyterlab/codemirror/lib/mode').Mode;

let realMode: ModeNamespace | undefined;
let loading: Promise<ModeNamespace> | undefined;

function loadMode(): Promise<ModeNamespace> {
  if (!loading) {
    loading = import(/* webpackChunkName: "codemirror" */ '@jupyterlab/codemirror/lib/mode').then(module => {
      realMode = module.Mode;
      return realMode;
    });
    // a failed load (e.g. network) may be retried by the next code block
    loading.catch(() => (loading = undefined));
  }
  return loading;
}

// CodeMirrorEditor.defaultConfig.theme of @jupyterlab/codemirror 3.x
export const CodeMirrorEditor = {
  defaultConfig: { theme: 'jupyter' }
};

export const Mode = {
  ensure(mode: any): Promise<any> {
    return loadMode().then(real => real.ensure(mode));
  },
  // only called after ensure resolved, so CodeMirror is loaded
  run(code: string, mode: any, el: HTMLElement): void {
    if (!realMode) {
      throw new Error('CodeMirror is not loaded, call Mode.ensure first');
    }
    realMode.run(code, mode, el);
  }
};
