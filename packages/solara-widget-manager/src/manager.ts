/***************************************************************************
 * Copyright (c) 2018, Voilà contributors                                   *
 * Copyright (c) 2018, QuantStack                                           *
 *                                                                          *
 * Distributed under the terms of the BSD 3-Clause License.                 *
 *                                                                          *
 * The full license is in the file LICENSE, distributed with this software. *
 ****************************************************************************/

import {
  WidgetManager as JupyterLabManager,
} from '@jupyter-widgets/jupyterlab-manager/lib/manager';

import {
  WidgetRenderer
} from '@jupyter-widgets/jupyterlab-manager/lib/renderer';


import * as output from '@jupyter-widgets/jupyterlab-manager/lib/output';

import * as base from '@jupyter-widgets/base';
import * as controls from '@jupyter-widgets/controls';
// there two imports came 'for free' with webpack 4, from the jupyter-lab-manager plugin
// it seems webpack 5 is better at tree-shaking, so we didn't need to import them explicitly before
import '@jupyter-widgets/base/css/index.css';
import '@jupyter-widgets/controls/css/widgets-base.css';
// Voila imports the following css file, not sure why
// import '@jupyter-widgets/controls/css/widgets.built.css';

import * as CoreUtils from '@jupyterlab/coreutils';
import * as OutputArea from '@jupyterlab/outputarea';

import { DocumentRegistry } from '@jupyterlab/docregistry';
import { INotebookModel } from '@jupyterlab/notebook';
import { IRenderMimeRegistry } from '@jupyterlab/rendermime';

import * as LuminoAlgorithm from '@lumino/algorithm';
import * as LuminoCommands from '@lumino/commands';
import * as LuminoDomutils from '@lumino/domutils';
import * as LuminoSignaling from '@lumino/signaling';
import * as LuminoVirtualdom from '@lumino/virtualdom';
import * as LuminoWidget from '@lumino/widgets';

import { MessageLoop } from '@lumino/messaging';

import { Widget } from '@lumino/widgets';

import { IComm } from '@jupyterlab/services/lib/kernel/kernel';
import { requireLoader } from './loader';


const WIDGET_MIMETYPE = 'application/vnd.jupyter.widget-view+json';

/**
 * Time (in ms) after which we consider the control comm target not responding.
 */
export const CONTROL_COMM_TIMEOUT = 500;

/**
 * A custom widget manager to render widgets with Voila
 */
export class WidgetManager extends JupyterLabManager {
  controlComm: IComm;
  controlCommHandler: { onMsg: (msg: any) => void; onClose: () => void; };
  constructor(
    context: DocumentRegistry.IContext<INotebookModel>,
    rendermime: IRenderMimeRegistry,
    settings: JupyterLabManager.Settings
  ) {
    super(context, rendermime, settings);
    rendermime.addFactory(
      {
        safe: false,
        mimeTypes: [WIDGET_MIMETYPE],
        createRenderer: options => new WidgetRenderer(options, this)
      },
      1
    );
    this._registerWidgets();
    this._loader = requireLoader;
    const kernel = context.sessionContext?.session?.kernel;
    this.connectControlComm();
    if (!kernel) {
      throw new Error('No current kernel');
    }
  }
  async connectControlComm() {
    const commId = base.uuid();
    const kernel = this.context.sessionContext?.session?.kernel;
    this.controlComm = kernel.createComm('solara.control', commId);
    this.controlCommHandler = {
      onMsg: (msg) => {
        console.error('No handler');
      },
      onClose: () => {
        console.error('No handler');
      }
    };
    this.controlComm.onMsg = async msg => {
      const data = msg['content']['data'];
      if (data.method === 'reload') {
        this.controlComm.send({ method: 'reload' });
      } else {
        await this.controlCommHandler.onMsg(msg);
      }
    };
    this.controlComm.onClose = async () => {
      await this.controlCommHandler.onClose();
    };
    this.controlComm.open({}, {}, [])
  }
  async appStatus() {
    // checks if app is still valid (e.g. server restarted and lost the widget state)
    // if we are connected to the same kernel, we'll get a reply instantly
    // however, if we are connected to a new kernel, we rely on the timeout
    // so every time we create a new comm.

    const kernel = this.context.sessionContext?.session?.kernel;
    const commId = base.uuid();
    const controlComm = kernel.createComm('solara.control', commId);
    controlComm.open({}, {}, [])
    try {
      return await new Promise((resolve, reject) => {
        controlComm.onMsg = (msg) => {
          const data = msg['content']['data'];
          if (data.method === 'app-status') {
            resolve({ started: data.started });
          }
          else {
            reject({ ok: false, message: "unexpected message" });
          }
        }
        controlComm.onClose = () => {
          console.error("closed solara control comm")
          reject({ ok: false, message: "closed solara control comm" });
        }
        setTimeout(() => {
          reject('timeout');
        }, CONTROL_COMM_TIMEOUT);
        controlComm.send({ method: 'app-status' });
      });
    } catch (e) {
      return { ok: false, message: e };
    }
  }

  async fetchAll() {
    // fetch all widgets
    await this._loadFromKernel();
  }

  async run(appName: string, args: any) {
    let { path } = args;
    // used for routing
    // should be similar to what we do in navigator.vue
    if (typeof path === 'undefined') {
      // backward compatibility, this was before we used <base>
      path = window.location.href.slice(document.baseURI.length);
    }
    const widget_id_promise = new Promise((resolve, reject) => {
      this.controlCommHandler = {
        onMsg: (msg) => {
          const data = msg['content']['data'];
          if (data.method === 'finished') {
            resolve(data.widget_id);
          }
          else {
            reject(data.error);
          }
        },
        onClose: () => {
          console.error("closed solara control comm")
          reject()
        }
      };
    });
    this.controlComm.send({ method: 'run', args: { ...args, appName: appName || null } });
    const widget_id = await widget_id_promise;
    return widget_id;
  }


  async display_view(msg: any, view: any, options: any): Promise<Widget> {
    if (options.el) {
      LuminoWidget.Widget.attach(view.pWidget, options.el);
    }
    if (view.el) {
      view.el.setAttribute('data-voila-jupyter-widget', '');
      view.el.addEventListener('jupyterWidgetResize', (e: Event) => {
        MessageLoop.postMessage(
          view.pWidget,
          LuminoWidget.Widget.ResizeMessage.UnknownSize
        );
      });
    }
    return view.pWidget;
  }

  async loadClass(
    className: string,
    moduleName: string,
    moduleVersion: string
  ): Promise<any> {
    if (
      moduleName === '@jupyter-widgets/base' ||
      moduleName === '@jupyter-widgets/controls' ||
      moduleName === '@jupyter-widgets/output'
    ) {
      return super.loadClass(className, moduleName, moduleVersion);
    } else {
      // TODO: code duplicate from HTMLWidgetManager, consider a refactor
      return this._loader(moduleName, moduleVersion).then(module => {
        if (module[className]) {
          return module[className];
        } else {
          return Promise.reject(
            'Class ' +
            className +
            ' not found in module ' +
            moduleName +
            '@' +
            moduleVersion
          );
        }
      });
    }
  }

  restoreWidgets(notebook: INotebookModel): Promise<void> {
    return Promise.resolve();
  }

  private _registerWidgets(): void {
    this.register({
      name: '@jupyter-widgets/base',
      version: base.JUPYTER_WIDGETS_VERSION,
      exports: base as any
    });
    this.register({
      name: '@jupyter-widgets/controls',
      version: controls.JUPYTER_CONTROLS_VERSION,
      exports: controls as any
    });
    this.register({
      name: '@jupyter-widgets/output',
      version: output.OUTPUT_WIDGET_VERSION,
      exports: output as any
    });
    // do this not top level, since requirejs might be loaded after this module is loaded
    if (typeof window !== 'undefined' && typeof window.define !== 'undefined') {
      window.define('@jupyter-widgets/base', base);
      window.define('@jupyter-widgets/controls', controls);
      window.define('@jupyter-widgets/output', output);

      window.define('@jupyterlab/coreutils', CoreUtils);
      window.define('@jupyterlab/outputarea', OutputArea);

      window.define('@phosphor/widgets', LuminoWidget);
      window.define('@phosphor/signaling', LuminoSignaling);
      window.define('@phosphor/virtualdom', LuminoVirtualdom);
      window.define('@phosphor/algorithm', LuminoAlgorithm);
      window.define('@phosphor/commands', LuminoCommands);
      window.define('@phosphor/domutils', LuminoDomutils);

      window.define('@lumino/widgets', LuminoWidget);
      window.define('@lumino/signaling', LuminoSignaling);
      window.define('@lumino/virtualdom', LuminoVirtualdom);
      window.define('@lumino/algorithm', LuminoAlgorithm);
      window.define('@lumino/commands', LuminoCommands);
      window.define('@lumino/domutils', LuminoDomutils);
    }
  }

  private _loader: (name: any, version: any) => Promise<any>;
}
