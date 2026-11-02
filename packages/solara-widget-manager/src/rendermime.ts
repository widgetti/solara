/***************************************************************************
 * Copyright (c) 2021, Voilà contributors                                   *
 * Copyright (c) 2021, QuantStack                                           *
 *                                                                          *
 * Distributed under the terms of the BSD 3-Clause License.                 *
 *                                                                          *
 * The full license is in the file LICENSE, distributed with this software. *
 ****************************************************************************/

// The output renderers (@jupyterlab/rendermime with marked, the apputils Sanitizer and translation,
// and the javascript renderer) are in the output-widget chunk (./chunks/output), the only user of
// a real registry. The core exports stand-ins with the same names, which are live bindings: once
// the chunk ran (at once when the page preloads it, as in full), they ARE the real class and lists,
// so such a page constructs a real RenderMimeRegistry, as before.
import { loadFeature } from './features';

type RenderMimeChunk = {
  RenderMimeRegistry: any;
  standardRendererFactories: ReadonlyArray<any>;
  extendedRendererFactories: ReadonlyArray<any>;
};

// markers for the real factory lists, which only exist once the chunk ran
const LAZY_STANDARD: ReadonlyArray<any> = Object.freeze([]);
const LAZY_EXTENDED: ReadonlyArray<any> = Object.freeze([]);

let chunk: RenderMimeChunk | null = null;
const pending: LazyRenderMimeRegistry[] = [];

function resolveFactories(factories: any): any {
  if (factories === LAZY_EXTENDED) {
    return chunk!.extendedRendererFactories;
  }
  if (factories === LAZY_STANDARD) {
    return chunk!.standardRendererFactories;
  }
  return factories;
}

/**
 * A RenderMimeRegistry before the output-widget chunk ran: it keeps its options and the factories
 * added to it, and delegates to a real registry (made with the same options and factories) once the
 * chunk runs. Only the Output widget renders outputs, and it loads the chunk first.
 */
class LazyRenderMimeRegistry {
  private _options: any;
  private _added: [any, number | undefined][] = [];
  private _real: any = null;

  constructor(options: any = {}) {
    this._options = { ...options };
    if (chunk) {
      this._materialize();
    } else {
      pending.push(this);
    }
  }

  /** @internal */
  _materialize(): void {
    if (this._real) {
      return;
    }
    const options = { ...this._options, initialFactories: resolveFactories(this._options.initialFactories) };
    this._real = new chunk!.RenderMimeRegistry(options);
    this._added.forEach(([factory, rank]) => this._real.addFactory(factory, rank));
    this._added = [];
  }

  private _need(what: string): any {
    if (!this._real) {
      loadFeature('output-widget').catch(console.error);
      throw new Error(`solara: RenderMimeRegistry.${what} needs the output-widget feature, which is not loaded yet`);
    }
    return this._real;
  }

  // the options, as fields of the real registry
  get translator(): any { return this._real ? this._real.translator : this._options.translator || null; }
  set translator(value: any) { this._real ? (this._real.translator = value) : (this._options.translator = value); }
  get resolver(): any { return this._real ? this._real.resolver : this._options.resolver || null; }
  set resolver(value: any) { this._real ? (this._real.resolver = value) : (this._options.resolver = value); }
  get linkHandler(): any { return this._real ? this._real.linkHandler : this._options.linkHandler || null; }
  set linkHandler(value: any) { this._real ? (this._real.linkHandler = value) : (this._options.linkHandler = value); }
  get latexTypesetter(): any { return this._real ? this._real.latexTypesetter : this._options.latexTypesetter || null; }
  set latexTypesetter(value: any) { this._real ? (this._real.latexTypesetter = value) : (this._options.latexTypesetter = value); }
  get sanitizer(): any { return this._real ? this._real.sanitizer : this._options.sanitizer || null; }
  set sanitizer(value: any) { this._real ? (this._real.sanitizer = value) : (this._options.sanitizer = value); }

  addFactory(factory: any, rank?: number): void {
    if (this._real) {
      this._real.addFactory(factory, rank);
    } else {
      // like the real registry, a factory replaces the earlier ones for its mime types: drop the
      // ones it replaces fully, so what they hold (each soft remount adds a factory that holds its
      // new widget manager) is freed, also when the output-widget chunk never loads
      const types = new Set(factory.mimeTypes);
      this._added = this._added.filter(([old]) => !old.mimeTypes.every((type: string) => types.has(type)));
      this._added.push([factory, rank]);
    }
  }

  clone(options: any = {}): any {
    if (this._real) {
      return this._real.clone(options);
    }
    const clone = new LazyRenderMimeRegistry({
      ...this._options,
      resolver: options.resolver || this.resolver || undefined,
      sanitizer: options.sanitizer || this._options.sanitizer || undefined,
      linkHandler: options.linkHandler || this.linkHandler || undefined,
      latexTypesetter: options.latexTypesetter || this.latexTypesetter || undefined,
    });
    clone._added = [...this._added];
    return clone;
  }

  get mimeTypes(): string[] { return this._need('mimeTypes').mimeTypes; }
  preferredMimeType(bundle: any, safe?: any): any { return this._need('preferredMimeType').preferredMimeType(bundle, safe); }
  createRenderer(mimeType: string): any { return this._need('createRenderer').createRenderer(mimeType); }
  createModel(options?: any): any { return this._need('createModel').createModel(options); }
  getFactory(mimeType: string): any { return this._need('getFactory').getFactory(mimeType); }
  removeMimeType(mimeType: string): void { this._need('removeMimeType').removeMimeType(mimeType); }
  getRank(mimeType: string): any { return this._need('getRank').getRank(mimeType); }
  setRank(mimeType: string, rank: number): void { this._need('setRank').setRank(mimeType, rank); }
}

export let RenderMimeRegistry: any = LazyRenderMimeRegistry;
export let standardRendererFactories: ReadonlyArray<any> = LAZY_STANDARD;
export let extendedRendererFactories: ReadonlyArray<any> = LAZY_EXTENDED;

/** Called by the output-widget chunk when it runs. */
export function provideRenderMime(real: RenderMimeChunk): void {
  if (chunk) {
    return;
  }
  chunk = real;
  RenderMimeRegistry = real.RenderMimeRegistry;
  standardRendererFactories = real.standardRendererFactories;
  extendedRendererFactories = real.extendedRendererFactories;
  pending.splice(0).forEach(registry => registry._materialize());
}
