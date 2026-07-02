
var jupyterWidgetMountPoint = {
    data() {
        return {
            renderFn: undefined,
            elem: undefined,
        }
    },
    props: ['mount-id'],
    created() {
        requestWidget(this.mountId);
    },
    mounted() {
        const vue3 = Vue.version.startsWith('3');
        requestWidget(this.mountId)
            .then(widgetView => {
                if (['VuetifyView', 'VuetifyTemplateView'].includes(widgetView.model.get('_view_name'))) {
                    this.renderFn = createElement => widgetView.vueRender(createElement);
                } else {
                    while (this.$el.firstChild) {
                        this.$el.removeChild(this.$el.firstChild);
                    }

                    requirejs(['@jupyter-widgets/base'], widgets =>
                        widgets.JupyterPhosphorWidget.attach(widgetView.pWidget, this.$el)
                    );
                }
            }
            );
    },
    render(createElement) {
        // in vue3 we have Vue.h, otherwise fall back to createElement (vue2)
        let h = Vue.h || createElement;
        if (this.renderFn) {
            /* workaround for v-menu click */
            if (!this.elem) {
                this.elem = this.renderFn(createElement);
            }
            return this.elem;
        }
        return h('div', this.$slots.default ||
            [h('v-chip', `[${this.mountId}]`)]);
    }
};

const widgetResolveFns = {};
const widgetPromises = {};

function provideWidget(mountId, widgetView) {
    if (widgetResolveFns[mountId]) {
        widgetResolveFns[mountId](widgetView);
    } else {
        widgetPromises[mountId] = Promise.resolve(widgetView);
    }
}

function requestWidget(mountId) {
    if (!widgetPromises[mountId]) {
        widgetPromises[mountId] = new Promise(resolve => widgetResolveFns[mountId] = resolve);
    }
    return widgetPromises[mountId];
}

function injectDebugMessageInterceptor(kernel) {
    const _original_handle_message = kernel._handleMessage.bind(kernel)
    kernel._handleMessage = ((msg) => {
        if (msg.msg_type === 'error') {
            app.$data.solaraDebugMessages.push({
                cell: '_',
                traceback: msg.content.traceback.map(line => ansiSpan(_.escape(line)))
            });
        } else if (msg.msg_type === 'stream' && (msg.content['name'] === 'stdout' || msg.content['name'] === 'stderr')) {
            app.$data.solaraDebugMessages.push({
                cell: '_',
                name: msg.content.name,
                text: msg.content.text
            });
        }
        return _original_handle_message(msg);
    })
}


function getCookiesMap(cookiesString) {
    return cookiesString.split(";")
        .map(function (cookieString) {
            return cookieString.trim().split("=");
        })
        .reduce(function (acc, curr) {
            acc[curr[0]] = curr[1];
            return acc;
        }, {});
}
const COOKIE_KEY_CONTEXT_ID = 'solara-session-id'


// from https://gist.github.com/outbreak/316637cde245160c2579898b21837c1c
function generateUuid() {
    function getRandomSymbol(symbol) {
        var array;

        if (symbol === 'y') {
            array = ['8', '9', 'a', 'b'];
            return array[Math.floor(Math.random() * array.length)];
        }

        array = new Uint8Array(1);
        window.crypto.getRandomValues(array);
        return (array[0] % 16).toString(16);
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, getRandomSymbol);
}

async function solaraInit(mountId, appName) {
    console.log('solara init', mountId, appName);
    define("vue", [], () => Vue);
    define("vuetify", [], () => Vuetify);
    cookies = getCookiesMap(document.cookie);
    const searchParams = new URLSearchParams(window.location.search);
    let kernelId = searchParams.get('kernelid') || generateUuid()
    let unloading = false;
    window.addEventListener('beforeunload', function (e) {
        unloading = true;
        kernel.dispose()
        // allow to opt-out to make testing easier
        if (!searchParams.has('solara-no-close-beacon')) {
            window.navigator.sendBeacon(close_url);
        }
    });
    let kernel = await solara.connectKernel(solara.jupyterRootPath, kernelId)
    if (!kernel) {
        return;
    }
    const close_url = `${solara.rootPath}/_solara/api/close/${kernelId}?session_id=${kernel.clientId}`;
    let skipReconnectedCheck = true;
    // re-entrancy + flapping guard for the soft-remount (§6.2)
    let remountInProgress = false;

    // debug/test hooks on the solara JS global (§6.4): always-on, unstable-by-contract. Getters
    // return the CURRENT closure values because the socket is replaced on every reconnect and the
    // widget manager on every soft-remount, so captured references go stale by design.
    solara.debug = {
        kernel: () => kernel,
        widgetManager: () => widgetManager,
        ws: () => kernel && kernel._ws,
        connectionStatus: kernel.connectionStatus,
        reconnectCount: 0,
        remountCount: 0,
        lastRestore: null,
        dropConnection() {
            // close the raw underlying socket WITHOUT kernel.dispose, so the jupyterlab-services
            // reconnect machinery fires as on a network blip. kernel._ws is a private field of the
            // vendored bundle - guard against a bundle change.
            if (!kernel._ws) {
                console.warn('solara.debug: kernel._ws not found (bundle change?)');
                return false;
            }
            kernel._ws.close();
            return true;
        },
        async simulateFailover() {
            // evict the kernel context server-side (dev/test-gated route), then drop the socket, so
            // the reconnect behaves exactly like landing on a fresh instance - with only backend
            // state surviving. With the memory backend this exercises the real restore path in a
            // single dev process (§6.5).
            try {
                await fetch(`${solara.rootPath}/_solara/api/evict/${kernelId}`, { method: 'POST', credentials: 'same-origin' });
            } catch (e) {
                console.warn('solara.debug.simulateFailover: evict request failed', e);
            }
            return this.dropConnection();
        },
    };

    // build a fresh widget manager from the same construction args as the initial mount, so the
    // initial path and the soft-remount path share one construction (§6.2)
    function makeWidgetManager() {
        return new solara.WidgetManager(context, rendermime, settings);
    }

    async function fallbackToDialog() {
        // the refresh-dialog path (recovery disabled, bundle changed, bailout, popout, or a failed
        // remount). shutdownKernel lives ONLY here.
        app.$data.needsRefresh = true;
        await solara.shutdownKernel(kernel);
    }

    async function solaraAppStatus(k) {
        // inline control-comm probe (mirrors solara-widget-manager appStatus) that returns the FULL
        // reply object - the bundled widgetManager.appStatus() drops canRecover/clientVersion/lastRestore.
        const controlComm = k.createComm('solara.control', generateUuid());
        controlComm.open({}, {}, []);
        return await new Promise((resolve, reject) => {
            controlComm.onMsg = (msg) => {
                const data = msg['content']['data'];
                if (data.method === 'app-status') {
                    resolve(data);
                } else {
                    reject(new Error('unexpected message on solara.control comm'));
                }
            };
            controlComm.onClose = () => reject(new Error('solara.control comm closed'));
            setTimeout(() => reject(new Error('app-status timeout')), 500);
            controlComm.send({ method: 'app-status' });
        });
    }

    async function solaraRemount() {
        if (remountInProgress) {
            // a reconnect arriving mid-remount is ignored; the in-progress attempt re-checks the
            // connection before its final swap (last completed attempt wins, §6.2)
            return;
        }
        if (searchParams.has('modelid')) {
            // popouts attach to a specific model id that no longer exists on a fresh instance -
            // there is nothing to soft-remount, so fall back to the dialog (§6.2)
            await fallbackToDialog();
            return;
        }
        remountInProgress = true;
        app.$data.remounting = true;
        try {
            // tear down the dead widget manager (disposes models). On a fresh kernel the old comms
            // are already gone server-side, so prefer the silent local teardown (bundle >= 0.5.0)
            // which does NOT send a comm_close per widget over the reconnected socket. Fall back to
            // clear_state() on older bundles (it sends comm_close - harmless, the server filters the
            // resulting "No such comm" noise). Bundle and pip versions are decoupled in the wild, so
            // the feature-detect is required.
            if (typeof widgetManager.clearStateLocal === 'function') {
                try {
                    await widgetManager.clearStateLocal();  // silent local teardown (bundle >= 0.5.0)
                } catch (e) {
                    console.warn('solara remount: clearStateLocal failed', e);
                }
            } else {
                try {
                    widgetManager.clear_state();  // old bundles: sends comm_close (server filters the noise)
                } catch (e) {
                    console.warn('solara remount: clear_state failed', e);
                }
            }
            if (typeof widgetManager.dispose === 'function') {
                try {
                    widgetManager.dispose();
                } catch (e) {
                    console.warn('solara remount: dispose failed', e);
                }
            }
            // settled promises would otherwise make the re-mount a no-op (§6.2)
            delete widgetPromises[mountId];
            delete widgetResolveFns[mountId];
            // destroy + recreate the Vue mount-point (bound :key in the loader templates)
            app.$data.remountKey += 1;
            // fresh widget manager on the same reconnected kernel
            widgetManager = makeWidgetManager();
            // pushState routing makes the boot-time path stale - recompute from the live URL now
            const path = window.location.pathname.slice(solara.rootPath.length) + window.location.search;
            const widgetModelId = await widgetManager.run(appName, { path, dark: inDarkMode(), themes: vuetifyThemes });
            if (kernel.connectionStatus !== 'connected') {
                // the socket dropped again during the remount - abort quietly; the next 'connected'
                // event restarts the flow
                return;
            }
            await solaraMount(widgetManager, mountId, widgetModelId);
            solara.debug.remountCount++;
        } catch (e) {
            console.error('solara remount failed', e);
            await fallbackToDialog();
        } finally {
            app.$data.remounting = false;
            remountInProgress = false;
        }
    }

    kernel.statusChanged.connect(() => {
        app.$data.kernelBusy = kernel.status == 'busy';
    });

    window.addEventListener('solara.router', function (event) {
        app.$data.urlHasChanged = true;
        if(kernel.status == 'busy') {
            app.$data.loadingPage = true;
        }
    });
    kernel.statusChanged.connect(() => {
        // When navigation is triggered from the front-end, kernel.status becoming busy and
        // solara.router event happen in a different order than when navigating through Python, so
        // if the URL has changed when the kernel becomes busy, we set loadingPage to true
        if (kernel.status == 'busy' && app.$data.urlHasChanged) {
            app.$data.loadingPage = true;
        }
        // the first idle after a loadingPage == true (a router event)
        // will be used as indicator that the page is loaded
        if (app.$data.loadingPage && kernel.status == 'idle') {
            app.$data.loadingPage = false;
            app.$data.urlHasChanged = false;
            const event = new Event('solara.pageReady');
            window.dispatchEvent(event);
        }
    });


    kernel.connectionStatusChanged.connect((s) => {
        if (unloading) {
            // we don't want to show ui changes when hitting refresh
            return;
        }
        app.$data.connectionStatus = s.connectionStatus;
        solara.debug.connectionStatus = s.connectionStatus;
        if (s.connectionStatus == 'connected') {
            app.$data.wasConnected = true;
        }
        if (s.connectionStatus == 'connected' && !skipReconnectedCheck) {
            solara.debug.reconnectCount++;
            (async () => {
                if (app.$data.needsRefresh) {
                    // already gave up
                    return;
                }
                // On reconnect we expect the app to still be started. If it is not, we either landed
                // on a different node/worker or the server restarted. Probe app-status and decide
                // (§6.1): started -> hot reconnect (fetchAll); recoverable AND matching client bundle
                // -> soft-remount (no dialog); otherwise -> refresh dialog.
                let reply;
                try {
                    reply = await solaraAppStatus(kernel);
                } catch (e) {
                    // no reply within the timeout - treat as not started and not recoverable
                    reply = { started: false, canRecover: false };
                }
                solara.debug.lastRestore = reply.lastRestore || null;
                if (reply.started) {
                    await widgetManager.fetchAll();
                } else if (reply.canRecover && reply.clientVersion === solara.clientVersion) {
                    await solaraRemount();
                } else {
                    await fallbackToDialog();
                }
            })();
        }
    })
    const context = {
        sessionContext: {
            session: {
                kernel,
                kernelChanged: {
                    connect: () => {
                    }
                },
            },
            statusChanged: {
                connect: () => {
                }
            },
            kernelChanged: {
                connect: () => {
                }
            },
            connectionStatusChanged: {
                connect: (s) => {
                }
            },
        },
        saveState: {
            connect: () => {
            }
        },
    };

    const settings = {
        saveState: false
    };

    // override the latexTypesetter to use katex, in case there are any libraries that
    // make use of that.
    const rendermime = new solara.RenderMimeRegistry({
        initialFactories: solara.extendedRendererFactories,
        latexTypesetter: new solara.KatexTypesetter(),
    });

    let widgetManager = makeWidgetManager();
    // it seems if we attach this to early, it will not be called
    app.$data.loading_text = 'Loading app';
    const path = window.location.pathname.slice(solara.rootPath.length) + window.location.search;
    let widgetModelId = searchParams.get('modelid');
    // if kernelid and modelid are given as query parameters, we will use them
    // instead of running the current solara app. This allows usage such as
    // ipypopout, which reconnects to an existing kernel and shows a particular
    // widget.
    if (kernelId && widgetModelId) {
        await widgetManager.fetchAll();
    } else {
        widgetModelId = await widgetManager.run(appName, {path, dark: inDarkMode(), themes: vuetifyThemes});
    }
    await solaraMount(widgetManager, mountId || 'content', widgetModelId);
    skipReconnectedCheck = false;
    solara.renderKatex();
}

async function solaraMount(widgetManager, mountId, modelId) {
    console.log(`will mount widget with id ${modelId} at mount id ${mountId}`)

    async function init() {
        await Promise.all(Object.values(widgetManager._models).map(async (modelPromise) => {
            const model = await modelPromise;
            if (model.model_id == modelId) {
                const view = await widgetManager.create_view(model);
                provideWidget(mountId, view);
            }
        }));
        app.$data.loadingPercentage = 0;
        app.$data.loading_text = 'Done';
        app.$data.loading = false;
    }
    if (document.readyState === 'complete') {
        init()
    } else {
        window.addEventListener('load', init);
    }
}
