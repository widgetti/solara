/***************************************************************************
 * Copyright (c) 2018, Voilà contributors                                   *
 * Copyright (c) 2018, QuantStack                                           *
 *                                                                          *
 * Distributed under the terms of the BSD 3-Clause License.                 *
 *                                                                          *
 * The full license is in the file LICENSE, distributed with this software. *
 ****************************************************************************/

import { PageConfig } from '@jupyterlab/coreutils';
import { Kernel, ServerConnection } from '@jupyterlab/services';
import { KernelConnection } from '@jupyterlab/services/lib/kernel/default';
import * as KernelMessage from '@jupyterlab/services/lib/kernel/messages';



export async function connectKernel(
  baseUrl?: string,
  kernelId?: string,
  options?: Partial<ServerConnection.ISettings>
): Promise<Kernel.IKernelConnection | undefined> {
  baseUrl = baseUrl ?? PageConfig.getBaseUrl();
  kernelId = kernelId ?? PageConfig.getOption('kernelId');
  const serverSettings = ServerConnection.makeSettings({ baseUrl, ...options });

  // const model = await KernelAPI.getKernelModel(kernelId, serverSettings);
  // if (!model) {
  //   return;
  // }
  const model = { 'id': 'solara-id', 'name': 'solara-name' }
  const kernel = new KernelConnection({ model, serverSettings });
  return kernel;
}


export async function shutdownKernel(kernel) {
  // we cannot use this API since it uses the REST api
  // while we want to use the current websocket since this makes
  // sure the message gets delivered to the node/process where the
  // kernel is running
  // await kernel.shutdown();
  // so we use https://jupyter-protocol.readthedocs.io/en/latest/messaging.html#kernel-shutdown
  // @ts-ignore
  const msg = KernelMessage.createMessage({
    // @ts-ignore
    msgType: 'shutdown_request', channel: 'control', username: kernel._username, session: kernel._clientId, content: {
      // @ts-ignore
      'restart': false, // final shutdown, not a restart
    }
  });
  return await kernel.sendControlMessage(msg);
}
