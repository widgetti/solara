// feature "lumino": the parts of Lumino that the core does not use (the core keeps Widget, Panel,
// MessageLoop, @lumino/signaling, @lumino/domutils, ...), and the AMD modules @lumino/* and @phosphor/*
// that come from them (see ../amd). The app bundles split @lumino/widgets, algorithm and collections per
// file (tools/split-lumino.js), so the core gets only the files it imports, and this chunk the rest.
// The jupyter-controls and output-widget chunks load from here, so webpack runs them after this chunk,
// and they share its modules.
import * as LuminoAlgorithm from '@lumino/algorithm';
import * as LuminoCommands from '@lumino/commands';
import * as LuminoVirtualdom from '@lumino/virtualdom';
import * as LuminoWidget from '@lumino/widgets';

export const loadControls = () => import(/* webpackChunkName: "jupyter-controls" */ './controls');
export const loadOutput = () => import(/* webpackChunkName: "output-widget" */ './output');

export { LuminoAlgorithm, LuminoCommands, LuminoVirtualdom, LuminoWidget };
