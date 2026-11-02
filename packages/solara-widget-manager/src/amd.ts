// AMD (requirejs) modules for third-party widgets and nbextensions.
import * as base from '@jupyter-widgets/base';
import * as CoreUtils from '@jupyterlab/coreutils';

// the core has these two anyway (each is one file, and the core uses it); the other Lumino modules that
// requirejs can ask for are in the lumino chunk
import * as LuminoDomutils from '@lumino/domutils';
import * as LuminoSignaling from '@lumino/signaling';

import { loadFeature } from './features';

let defined = false;

/**
 * Define the AMD modules. Call this after require.js is loaded.
 * Feature modules (controls, output, and most of Lumino) are dormant named defines: their chunk
 * loads only when a module requires them, through the 'solara-feature!' plugin.
 * 'solara-feature!lumino:@lumino/widgets' loads the feature lumino, and names the module
 * @lumino/widgets in the warning when the page did not preload it.
 */
export function defineAmdModules(): void {
  if (defined || typeof window === 'undefined' || typeof window.define === 'undefined') {
    return;
  }
  defined = true;
  const define = window.define;
  // requirejs loader plugin: 'solara-feature!katex' resolves to the module of the feature chunk
  define('solara-feature', [], () => ({
    load: (resource: string, _require: any, onload: any) => {
      const [name, module] = resource.split(':');
      loadFeature(name, module).then(onload, onload.error);
    },
  }));
  define('@jupyter-widgets/base', base);
  define('@jupyter-widgets/controls', ['solara-feature!jupyter-controls'], (chunk: any) => chunk.controls);
  define('@jupyter-widgets/output', ['solara-feature!output-widget'], (chunk: any) => chunk.output);
  define('@jupyterlab/outputarea', ['solara-feature!output-widget'], (chunk: any) => chunk.OutputArea);

  define('@jupyterlab/coreutils', CoreUtils);

  for (const prefix of ['@phosphor', '@lumino']) {
    define(`${prefix}/signaling`, LuminoSignaling);
    define(`${prefix}/domutils`, LuminoDomutils);
    const lumino = (name: string, key: string) =>
      define(`${prefix}/${name}`, [`solara-feature!lumino:${prefix}/${name}`], (chunk: any) => chunk[key]);
    lumino('widgets', 'LuminoWidget');
    lumino('virtualdom', 'LuminoVirtualdom');
    lumino('algorithm', 'LuminoAlgorithm');
    lumino('commands', 'LuminoCommands');
  }
}
