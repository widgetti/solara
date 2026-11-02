// feature "output-widget": the Output widget, the Jupyter output area, and the output renderers
// (the core has a lazy RenderMimeRegistry stand-in, see ../rendermime)
import * as output from '@jupyter-widgets/jupyterlab-manager/lib/output';
import * as OutputArea from '@jupyterlab/outputarea';
import {
  RenderMimeRegistry,
  standardRendererFactories,
  htmlRendererFactory,
  markdownRendererFactory,
  latexRendererFactory,
  svgRendererFactory,
  imageRendererFactory,
  textRendererFactory
} from '@jupyterlab/rendermime';
import { rendererFactory as javascriptRendererFactory } from '@jupyterlab/javascript-extension';
import { provideRenderMime } from '../rendermime';

const extendedRendererFactories = [
  htmlRendererFactory,
  markdownRendererFactory,
  latexRendererFactory,
  svgRendererFactory,
  imageRendererFactory,
  javascriptRendererFactory,
  textRendererFactory
];

provideRenderMime({ RenderMimeRegistry, standardRendererFactories, extendedRendererFactories });

export { output, OutputArea };
