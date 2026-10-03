// AMD (requirejs) modules for third-party widgets and nbextensions.
import * as base from '@jupyter-widgets/base';
import * as CoreUtils from '@jupyterlab/coreutils';

import * as LuminoAlgorithm from '@lumino/algorithm';
import * as LuminoCommands from '@lumino/commands';
import * as LuminoDomutils from '@lumino/domutils';
import * as LuminoSignaling from '@lumino/signaling';
import * as LuminoVirtualdom from '@lumino/virtualdom';
import * as LuminoWidget from '@lumino/widgets';

import { loadFeature } from './features';

let defined = false;

/**
 * Define the AMD modules. Call this after require.js is loaded.
 * Feature modules (controls, output) are dormant named defines: their chunk
 * loads only when a module requires them, through the 'solara-feature!' plugin.
 */
export function defineAmdModules(): void {
  if (defined || typeof window === 'undefined' || typeof window.define === 'undefined') {
    return;
  }
  defined = true;
  const define = window.define;
  // requirejs loader plugin: 'solara-feature!katex' resolves to the module of the feature chunk
  define('solara-feature', [], () => ({
    load: (name: string, _require: any, onload: any) => {
      loadFeature(name).then(onload, onload.error);
    },
  }));
  define('@jupyter-widgets/base', base);
  define('@jupyter-widgets/controls', ['solara-feature!jupyter-controls'], (chunk: any) => chunk.controls);
  define('@jupyter-widgets/output', ['solara-feature!output-widget'], (chunk: any) => chunk.output);
  define('@jupyterlab/outputarea', ['solara-feature!output-widget'], (chunk: any) => chunk.OutputArea);

  define('@jupyterlab/coreutils', CoreUtils);

  define('@phosphor/widgets', LuminoWidget);
  define('@phosphor/signaling', LuminoSignaling);
  define('@phosphor/virtualdom', LuminoVirtualdom);
  define('@phosphor/algorithm', LuminoAlgorithm);
  define('@phosphor/commands', LuminoCommands);
  define('@phosphor/domutils', LuminoDomutils);

  define('@lumino/widgets', LuminoWidget);
  define('@lumino/signaling', LuminoSignaling);
  define('@lumino/virtualdom', LuminoVirtualdom);
  define('@lumino/algorithm', LuminoAlgorithm);
  define('@lumino/commands', LuminoCommands);
  define('@lumino/domutils', LuminoDomutils);
}
