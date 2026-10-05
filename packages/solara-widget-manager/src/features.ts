// Frontend features. Each feature is one named webpack chunk of the app bundle:
// <bundle>.<feature>.min.js and/or main<M>.<feature>.css.
// The server adds a <script>/<link> tag for every enabled feature, and
// loadPreloadedFeaturesSync() runs those chunks at once, so the globals they set
// exist synchronously. Any other feature lazy loads on first use (webpack fetches
// the JS and the CSS), with one console warning that names the flag to add.

type Loader = () => Promise<any>;
type Feature = { loader: Loader; needs: string[]; cssOnly: boolean; weakId?: any };

declare const require: any;
declare const __webpack_require__: any;
declare const __webpack_modules__: any;

const features: { [name: string]: Feature } = {};
// features the user does not choose: they load silently with the feature that needs them
const internalFeatures = new Set<string>(['sanitizer']);
// null: setEnabledFeatures was never called (a page without chunk tags, e.g. an old
// template), so nothing is preloaded and everything lazy loads without a warning
let enabledNames: string[] | null = null;
const loading = new Map<string, Promise<any>>();
const loaded = new Map<string, any>();
// the lazy loaded features, each with the AMD module that asked for it (or undefined)
const lazyLoaded: [string, string | undefined][] = [];
const lazyLoadCallbacks: ((name: string, module?: string) => void)[] = [];

/**
 * Register a feature. weakId is require.resolveWeak(<chunk root>), which lets
 * loadPreloadedFeaturesSync run a preloaded chunk without import().
 * A css-only feature has no code: when enabled, the server's <link> is all it needs.
 */
export function registerFeature(name: string, loader: Loader, needs: string[] = [], cssOnly = false, weakId?: any): void {
  features[name] = { loader, needs, cssOnly, weakId };
}

/** A feature whose code is part of the core bundle (e.g. Vuetify on Vue 2): always loaded, never warns. */
export function provideFeature(name: string, module: any): void {
  registerFeature(name, () => Promise.resolve(module));
  loaded.set(name, module);
  loading.set(name, Promise.resolve(module));
}

/** The features the server preloaded (the --frontend setting). Their requirements count as enabled too. */
export function setEnabledFeatures(names: string[]): void {
  enabledNames = [...names];
}

function enabledSet(): Set<string> {
  const result = new Set<string>();
  const add = (name: string) => {
    if (!result.has(name)) {
      result.add(name);
      (features[name]?.needs || []).forEach(add);
    }
  };
  (enabledNames || []).forEach(add);
  return result;
}

export function isEnabled(name: string): boolean {
  return enabledNames !== null && enabledSet().has(name);
}

export function hasFeature(name: string): boolean {
  return name in features;
}

export function getLoadedFeature(name: string): any {
  return loaded.get(name);
}

/**
 * Called once per lazy loaded feature, with the AMD module that asked for it, if any (e.g. '@phosphor/widgets'
 * for lumino); also for lazy loads that happened before the callback was added.
 */
export function onLazyLoad(callback: (name: string, module?: string) => void): void {
  lazyLoadCallbacks.push(callback);
  lazyLoaded.forEach(([name, module]) => callback(name, module));
}

function warnLazyLoad(name: string, module?: string): void {
  if (lazyLoaded.some(([loadedName]) => loadedName === name)) {
    return;
  }
  lazyLoaded.push([name, module]);
  console.warn(
    `solara: frontend feature "${name}" was not preloaded, it loads now` +
    (module ? ` for the requirejs module "${module}"` : '') +
    `. Add "+${name}" to --frontend (SOLARA_FRONTEND) to preload it.`
  );
  lazyLoadCallbacks.forEach(callback => {
    try {
      callback(name, module);
    } catch (e) {
      console.error(e);
    }
  });
}

// the features that a widget used, but that the page does not load and that never load on first use (jquery, see ./jquery)
const missingReported: string[] = [];
const missingCallbacks: ((name: string) => void)[] = [];

/** Called once per feature that a widget used but the page does not load; also for the ones reported before. */
export function onMissingFeature(callback: (name: string) => void): void {
  missingCallbacks.push(callback);
  missingReported.forEach(name => callback(name));
}

/** A widget used a feature that the page does not load (the caller shows the error). Reports each feature once. */
export function reportMissingFeature(name: string): void {
  if (missingReported.indexOf(name) !== -1) {
    return;
  }
  missingReported.push(name);
  missingCallbacks.forEach(callback => {
    try {
      callback(name);
    } catch (e) {
      console.error(e);
    }
  });
}

function load(name: string, warn: boolean, module?: string): Promise<any> {
  let promise = loading.get(name);
  if (promise) {
    return promise;
  }
  const feature = features[name];
  if (!feature) {
    return Promise.reject(new Error(`solara: unknown frontend feature "${name}"`));
  }
  if (isEnabled(name) && feature.cssOnly) {
    // the server emitted the <link>, there is nothing to fetch
    loaded.set(name, {});
    promise = Promise.resolve({});
  } else {
    if (warn && enabledNames !== null && !isEnabled(name) && !internalFeatures.has(name)) {
      warnLazyLoad(name, module);
    }
    // requirements load silently: the warning names the feature that needs them
    const needs = feature.needs.map(need => load(need, false));
    promise = Promise.all([...needs, feature.loader()]).then(results => {
      const module = results[results.length - 1];
      loaded.set(name, module);
      return module;
    });
    // a failed load (e.g. network) may be retried later
    promise.catch(() => loading.delete(name));
  }
  loading.set(name, promise);
  return promise;
}

/**
 * Returns the feature's module, loading it (and its requirements) when needed.
 * module: the AMD module that asked for it, for the warning of a lazy load.
 */
export function loadFeature(name: string, module?: string): Promise<any> {
  return load(name, true, module);
}

function loadSync(name: string, missing: string[]): void {
  const feature = features[name];
  if (!feature || loaded.has(name) || missing.indexOf(name) !== -1) {
    return;
  }
  feature.needs.forEach(need => loadSync(need, missing));
  if (feature.cssOnly) {
    loaded.set(name, {});
    loading.set(name, Promise.resolve({}));
    return;
  }
  const id = feature.weakId;
  if (id === undefined) {
    // not a chunk of this bundle (e.g. mermaid): loads on first use, without a warning
    return;
  }
  if (!__webpack_modules__[id] || feature.needs.some(need => missing.indexOf(need) !== -1)) {
    // the chunk <script> did not run (yet), or a chunk it needs did not (its code uses the modules of that
    // chunk, e.g. jupyter-controls uses Lumino of the lumino chunk): it stays async, and loads what it
    // needs on first use
    missing.push(name);
    return;
  }
  const module = __webpack_require__(id);
  loaded.set(name, module);
  loading.set(name, Promise.resolve(module));
}

/**
 * Synchronously run the root module of every enabled feature whose chunk <script> already ran.
 * Returns the names of enabled chunk features that are not there.
 */
export function loadPreloadedFeaturesSync(): string[] {
  const missing: string[] = [];
  if (enabledNames !== null) {
    enabledSet().forEach(name => loadSync(name, missing));
  }
  return missing;
}

// the built-in features of the widget manager
registerFeature(
  'jupyter-css',
  () => import(/* webpackChunkName: "jupyter-css" */ './chunks/jupyter-css'),
  [],
  true,
);
registerFeature(
  'sanitizer',
  () => import(/* webpackChunkName: "sanitizer" */ './chunks/sanitizer'),
  [],
  false,
  require.resolveWeak('./chunks/sanitizer'),
);
// jQuery: never loads on first use (see ./jquery), only when the page preloads it or as a requirement of a feature
registerFeature(
  'jquery',
  () => import(/* webpackChunkName: "jquery" */ './chunks/jquery'),
  [],
  false,
  require.resolveWeak('./chunks/jquery'),
);
registerFeature(
  'lumino',
  () => import(/* webpackChunkName: "lumino" */ './chunks/lumino'),
  [],
  false,
  require.resolveWeak('./chunks/lumino'),
);
// These chunks load from the lumino chunk (and run after it), so they share its modules. They also use jQuery
// (for example jQuery UI's slider in the ipywidgets 7 controls, which needs it when its module runs), so they load
// only after the jquery chunk ran.
const afterLuminoAndJQuery = (): Promise<any> =>
  Promise.all([load('lumino', false), load('jquery', false)]).then(([lumino]) => lumino);
registerFeature(
  'jupyter-controls',
  () => afterLuminoAndJQuery().then(lumino => lumino.loadControls()),
  ['jupyter-css', 'sanitizer', 'lumino', 'jquery'],
  false,
  require.resolveWeak('./chunks/controls'),
);
registerFeature(
  'output-widget',
  () => afterLuminoAndJQuery().then(lumino => lumino.loadOutput()),
  ['jupyter-css', 'sanitizer', 'lumino', 'jquery'],
  false,
  require.resolveWeak('./chunks/output'),
);
registerFeature(
  'katex',
  () => import(/* webpackChunkName: "katex" */ './chunks/katex'),
  [],
  false,
  require.resolveWeak('./chunks/katex'),
);
