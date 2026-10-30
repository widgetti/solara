// The parts of the @jupyterlab/services index that the bundled code uses. The app bundles
// replace the index (lib/index.js) with this module, so the rest of the package (contents,
// sessions, terminals, settings, ...) is not bundled.
import * as KernelMessage from '@jupyterlab/services/lib/kernel/messages';

export { ServerConnection } from '@jupyterlab/services/lib/serverconnection';
export { KernelMessage };
