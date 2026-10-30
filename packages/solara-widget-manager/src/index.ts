/***************************************************************************
 * Copyright (c) 2018, Voilà contributors                                   *
 * Copyright (c) 2018, QuantStack                                           *
 *                                                                          *
 * Distributed under the terms of the BSD 3-Clause License.                 *
 *                                                                          *
 * The full license is in the file LICENSE, distributed with this software. *
 ****************************************************************************/

export {
  RenderMimeRegistry,
  standardRendererFactories
} from '@jupyterlab/rendermime';
export { connectKernel, shutdownKernel } from './kernel';
export { WidgetManager } from './manager';
export { KatexTypesetter, renderKatex, loadKatex } from './katex';
export { extendedRendererFactories } from './rendermime';
export {
  registerFeature,
  provideFeature,
  setEnabledFeatures,
  isEnabled,
  hasFeature,
  loadFeature,
  loadPreloadedFeaturesSync,
  getLoadedFeature,
  onLazyLoad
} from './features';
export { defineAmdModules } from './amd';
