// The stand-in for jQuery in the core. jQuery itself is the frontend feature "jquery" (./chunks/jquery), which `full`
// preloads and `minimal` leaves out. It never loads on first use: a widget uses jQuery without asking for it first.
//
// Every 'jquery' import of the app bundle (@jupyter-widgets/base, Backbone, the controls, the Output widget, jQuery UI)
// gets this $, through ./jquery-cjs (the "jquery$" alias in the webpack configs of the apps).
// - Until the jquery chunk runs, $(node) wraps the DOM nodes in an array-like object ($el[0], $el.length).
//   @jupyter-widgets/base calls $(el) for every view (view.$el), also for Vue views, which use no more than that.
//   Any other use of jQuery throws an error that names +jquery: $(selector), $(html), $(function), $.ajax, $.fn,
//   and every jQuery method on a wrapper, for example view.$el.empty().
// - The jquery chunk calls setJQuery. From then on, $ forwards to the real jQuery: $(...), $.ajax, and also the
//   $.fn.slider = ... and $.cleanData = ... of plugins such as jQuery UI. `full` and +jquery run that chunk before
//   the first view, so every view.$el is a real jQuery object, as before. A wrapper made before then stays a wrapper.
import { reportMissingFeature } from './features';

let real: any = null;
let logged = false;

function missing(what: string): Error {
  const when = real ? 'loaded only after this view was made' : 'does not load';
  const message =
    `solara: this widget uses jQuery (${what}), which this page ${when}. ` +
    'Add +jquery to --frontend (SOLARA_FRONTEND), for example --frontend=minimal,+jquery.';
  if (!logged) {
    // once: ipywidgets 8 shows the error in the error view of the widget, but does not log it
    logged = true;
    console.error(message);
    reportMissingFeature('jquery');
  }
  return new Error(message);
}

// Names that code reads from any object to find out what it is, and that jQuery objects do not have: webpack's
// __esModule, Vue's __v_skip, React's $$typeof, an index past the end, and the then and toJSON of Promise and JSON.
// They give what a plain object gives (undefined), as do the names that a plain object (or a function) has.
const PROBE = /^([_$0-9]|then$|toJSON$)/;

function isProbe(target: object, name: string | symbol): boolean {
  return typeof name === 'symbol' || name in target || PROBE.test(name);
}

// The prototype of a wrapper: any other name is a jQuery method (empty, append, css, find, on, ...), so reading it throws.
const wrapperPrototype = new Proxy(
  {},
  {
    get(target, name, receiver) {
      if (isProbe(target, name)) {
        return Reflect.get(target, name, receiver);
      }
      throw missing(`.${String(name)}()`);
    },
  }
);

function wrap(nodes: any[]): any {
  const wrapper = Object.create(wrapperPrototype);
  nodes.forEach((node, i) => (wrapper[i] = node));
  wrapper.length = nodes.length;
  return wrapper;
}

function call(...args: any[]): any {
  if (real) {
    return real(...args);
  }
  const selector = args[0];
  if (selector === undefined || selector === null || selector === '') {
    return wrap([]);
  }
  if (Object.getPrototypeOf(selector) === wrapperPrototype) {
    return selector;
  }
  if (selector.nodeType || selector === selector.window) {
    return wrap([selector]);
  }
  throw missing(typeof selector === 'function' ? '$(function)' : `$(${JSON.stringify(String(selector).slice(0, 40))})`);
}
// el instanceof $, until the real jQuery is there
call.prototype = wrapperPrototype;

const $: any = new Proxy(call, {
  get(target, name) {
    if (real) {
      return real[name];
    }
    if (isProbe(target, name)) {
      return Reflect.get(target, name);
    }
    throw missing(`$.${String(name)}`);
  },
  set(target, name, value) {
    if (!real) {
      throw missing(`$.${String(name)}`);
    }
    real[name] = value;
    return true;
  },
  has(target, name) {
    return real ? name in real : Reflect.has(target, name);
  },
});

/** Called by the jquery chunk: from now on, $ is the real jQuery. */
export function setJQuery(jQuery: any): void {
  real = jQuery;
}

export default $;
