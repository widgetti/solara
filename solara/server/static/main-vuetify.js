
const widgetViews = {};
var jupyterWidgetMountPoint = {
    data() {
        return {
            renderFn: undefined,
            elem: undefined,
        }
    },
    props: ['mount-id'],
    created() {
        const maybeCreateRenderFn = (widgetView) => {
            // in solara, this is always the case, but lets keep this code so we could potentially
            // support any ipywidget as a root view
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
        maybeCreateRenderFn(widgetViews[this.mountId]);
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
    mountId = mountId || 'content';
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
    // reconnect state machine state (see the block comment above connectionStatusChanged):
    // every 'connected' event starts a reconnect CYCLE owning this generation; a cycle that is
    // no longer the latest (or whose socket dropped again) aborts silently. A monotonic counter
    // cannot deadlock the way an in-flight boolean could (there is nothing to clear).
    let reconnectGeneration = 0;
    // true iff a root view was mounted and not torn down since. Every rebuild sets it false
    // FIRST and true only after a completed mount, so an interrupted rebuild (socket drop
    // mid-way) leaves viewMounted == false for the next cycle to detect and REPAIR.
    let viewMounted = false;

    // Purge orphaned comm registrations left on the kernel CONNECTION after a widget manager is
    // torn down. jupyter-widgets' WidgetModel.close(true) (used by clearStateLocal for a silent
    // local teardown) deletes the model's reference to its comm but does NOT unregister the
    // CommHandler from the connection's private _comms map (close(true) skips comm.close()). Those
    // orphans are inert on the same node, but on a reconnect that lands on a DIFFERENT node still
    // serving one of those ids, the resync (_loadFromKernel -> createComm(id)) throws
    // "Comm is already created" mid-map, leaving half the widget tree detached (inputs never sync
    // to python again). Disposing the CommHandler runs its unregister callback WITHOUT sending a
    // comm_close over the wire (matching clearStateLocal's silent intent). commIdsBefore is
    // snapshotted before the new manager registers its fresh comms, so we never purge live ones.
    function purgeStaleComms(commIdsBefore) {
        const comms = kernel && kernel._comms;
        if (!comms || typeof comms.get !== 'function') {
            // bundle change (private field renamed): skip rather than throw - the collision is
            // rare (needs a cross-node reconnect) and must not break the common reconnect path.
            return;
        }
        for (const id of commIdsBefore) {
            const comm = comms.get(id);
            if (comm && typeof comm.dispose === 'function') {
                try {
                    comm.dispose();
                } catch (e) {
                    console.warn('solara remount: stale comm dispose failed', e);
                }
            }
        }
    }

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
        viewMounted: () => viewMounted,
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
            // evict the kernel context server-side (dev/test-gated), then drop the socket, so
            // the reconnect behaves exactly like landing on a fresh instance - with only backend
            // state surviving. With the memory backend this exercises the real restore path in a
            // single dev process (§6.5).
            // The evict goes over the kernel WEBSOCKET (solara.control comm), not HTTP: behind a
            // round-robin load balancer an HTTP evict lands on an arbitrary instance and 404s on
            // every non-owner, while the websocket by definition terminates on the instance that
            // owns the kernel. A refused evict (gate off) still fails loud: dropping the socket
            // anyway would reconnect to the SAME live context - a silent no-op that looks like a
            // passing failover to a developer or CI.
            let status;
            try {
                status = await new Promise((resolve, reject) => {
                    const controlComm = kernel.createComm('solara.control', generateUuid());
                    controlComm.open({}, {}, []);
                    controlComm.onMsg = (msg) => {
                        const data = msg['content']['data'];
                        if (data.method === 'evict') {
                            resolve(data.status);
                        }
                    };
                    setTimeout(() => reject(new Error('evict reply timeout')), 2000);
                    controlComm.send({ method: 'evict' });
                });
            } catch (e) {
                console.warn('solara.debug.simulateFailover: evict over websocket failed', e);
                return false;
            }
            if (status !== 'evicted') {
                console.warn('solara.debug.simulateFailover: evict refused; kernel not evicted. ' +
                    'Enable it with SOLARA_STATE_TEST_EVICTION=true (non-production only).');
                return false;
            }
            // the server also closes the socket while tearing the kernel down; drop it here too
            // so the reconnect machinery fires even if that races
            this.dropConnection();
            return true;
        },
    };

    // build a fresh widget manager from the same construction args as the initial mount, so the
    // initial path and the soft-remount path share one construction (§6.2)
    function makeWidgetManager() {
        return new solara.WidgetManager(context, rendermime, settings);
    }

    async function fallbackToDialog() {
        // the GIVE-UP verdict (recovery disabled, bundle changed, bailout, popout, consistent
        // probe failure, or a failed rebuild). shutdownKernel lives ONLY here, and this is only
        // ever called by the latest live cycle (see the state machine comment).
        app.$data.remounting = false;
        app.$data.needsRefresh = true;
        await solara.shutdownKernel(kernel);
    }

    async function solaraAppStatus(k, timeoutMs) {
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
            setTimeout(() => reject(new Error('app-status timeout')), timeoutMs);
            controlComm.send({ method: 'app-status' });
        });
    }

    async function probeAppStatus(superseded) {
        // PROBE step of the reconnect cycle. Returns the reply object, a synthetic
        // {started:false, canRecover:false} after CONSISTENT failure (that is a real verdict),
        // or null when the cycle got superseded mid-probe (abort silently - a probe riding a
        // dead transport, or raced by a newer cycle, proves nothing about the app's health).
        // The give-up verdict tears a session down for good (dialog, and with forceRefresh a
        // full page reload), so it must never follow a SINGLE late/lost reply: one blip (busy
        // backend restoring another kernel, network jitter) would otherwise kill a perfectly
        // recoverable session.
        for (let attempt = 1; attempt <= 3; attempt++) {
            try {
                const reply = await solaraAppStatus(kernel, 2000);
                return superseded() ? null : reply;
            } catch (e) {
                console.warn(`solara reconnect: app-status probe attempt ${attempt} failed`, e);
                if (superseded()) {
                    return null;
                }
                if (attempt < 3) {
                    // brief backoff, then retry on a fresh comm
                    await new Promise((resolve) => setTimeout(resolve, 250 * attempt));
                    if (superseded()) {
                        return null;
                    }
                }
            }
        }
        return { started: false, canRecover: false };
    }

    async function teardownClientWidgets(superseded) {
        // shared teardown for REMOUNT/REPAIR: silently dispose the widget-manager generation
        // that is current ON ENTRY (a live one, or the remnants of an interrupted rebuild),
        // purge its comm registrations, and install a fresh manager + mount point. Returns the
        // fresh manager, or null when the cycle got superseded mid-teardown: the shared mount
        // state then already belongs to the newer cycle's own rebuild and must not be touched
        // (a stale teardown finishing late would otherwise dispose the fresh manager the newer
        // cycle just installed).
        const manager = widgetManager;
        // Snapshot the comm ids registered on the connection BEFORE teardown, so we can purge the
        // ones orphaned by the silent teardown below (see purgeStaleComms). Taken before the new
        // manager runs, so it can only ever name comms from the generation we are tearing down.
        const commIdsBefore = (kernel && kernel._comms && typeof kernel._comms.keys === 'function')
            ? [...kernel._comms.keys()]
            : [];
        // tear down the dead widget manager (disposes models). On a fresh kernel the old comms
        // are already gone server-side, so prefer the silent local teardown (bundle >= 0.5.0)
        // which does NOT send a comm_close per widget over the reconnected socket. Fall back to
        // clear_state() on older bundles (it sends comm_close - harmless, the server filters the
        // resulting "No such comm" noise). Bundle and pip versions are decoupled in the wild, so
        // the feature-detect is required.
        if (typeof manager.clearStateLocal === 'function') {
            try {
                await manager.clearStateLocal();  // silent local teardown (bundle >= 0.5.0)
            } catch (e) {
                console.warn('solara remount: clearStateLocal failed', e);
            }
        } else {
            try {
                manager.clear_state();  // old bundles: sends comm_close (server filters the noise)
            } catch (e) {
                console.warn('solara remount: clear_state failed', e);
            }
        }
        if (typeof manager.dispose === 'function') {
            try {
                manager.dispose();
            } catch (e) {
                console.warn('solara remount: dispose failed', e);
            }
        }
        if (superseded()) {
            return null;
        }
        // the silent teardown above (clearStateLocal / close(true)) leaves the disposed
        // widgets' CommHandlers registered on the connection; purge them now, before the new
        // manager registers its own, so a later cross-node reconnect resync cannot collide.
        purgeStaleComms(commIdsBefore);
        // settled promises would otherwise make the re-mount a no-op (§6.2)
        delete widgetPromises[mountId];
        delete widgetResolveFns[mountId];
        // destroy + recreate the Vue mount-point (bound :key in the loader templates)
        app.$data.remountKey += 1;
        // fresh widget manager on the same reconnected kernel
        widgetManager = makeWidgetManager();
        return widgetManager;
    }

    async function rebuildView(superseded, containerId) {
        // REMOUNT (containerId null): run() the app again - the server restores persisted state
        // on its fresh kernel context (§6.2).
        // REPAIR (containerId given): the app is already running server-side but OUR view is
        // gone (a previous rebuild was interrupted mid-way): re-attach to the existing root
        // container - fetchAll + mount, the same path a popout uses to attach - so no server
        // state is lost.
        if (searchParams.has('modelid')) {
            // popouts attach to a specific model id that no longer exists on a fresh instance -
            // there is nothing to rebuild, so fall back to the dialog (§6.2)
            await fallbackToDialog();
            return;
        }
        app.$data.remounting = true;
        // the view is going away NOW: if this rebuild never completes (socket drop mid-way,
        // lost run() reply), the next cycle sees viewMounted == false and REPAIRs (invariant 2)
        viewMounted = false;
        try {
            // work with OUR generation's manager from here on (never re-read the shared
            // binding after an await: a newer cycle's rebuild may have replaced it)
            const manager = await teardownClientWidgets(superseded);
            if (manager === null || superseded()) {
                return;
            }
            let modelId;
            if (containerId) {
                await manager.fetchAll();
                modelId = containerId;
            } else {
                // pushState routing makes the boot-time path stale - recompute from the live URL now
                const path = window.location.pathname.slice(solara.rootPath.length) + window.location.search;
                modelId = await manager.run(appName, { path, dark: inDarkMode(), themes: vuetifyThemes });
            }
            if (superseded()) {
                // the socket dropped again (or a newer cycle took over) during the rebuild -
                // abort quietly; the next cycle detects viewMounted == false and repairs
                return;
            }
            await solaraMount(manager, mountId, modelId);
            viewMounted = true;
            solara.debug.remountCount++;
        } catch (e) {
            if (superseded()) {
                // a superseded rebuild's failure is not a verdict: its comms may simply have
                // been torn down by the newer cycle's own rebuild
                console.warn('solara rebuild aborted (superseded)', e);
                return;
            }
            console.error('solara remount failed', e);
            await fallbackToDialog();
        } finally {
            if (!superseded()) {
                // the latest cycle owns the "Restoring session..." indicator; a superseded
                // rebuild must not clear what the newer cycle just set
                app.$data.remounting = false;
            }
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


    // =====================================================================================
    // Reconnect state machine (design §6.1/§6.2)
    //
    // State (all per page, in this closure):
    //   reconnectGeneration   monotonic; every 'connected' event starts a new reconnect CYCLE
    //                         that owns its generation. superseded() means "a newer cycle
    //                         exists, or the socket dropped again"; a superseded cycle aborts
    //                         SILENTLY at its next await boundary - its observations are stale
    //                         and prove nothing about the app's health.
    //   viewMounted           true iff a root view was mounted and not torn down since. Every
    //                         rebuild flips it false first and true only after a completed
    //                         mount, so an interrupted rebuild is visible to the next cycle.
    //   app.$data.needsRefresh   terminal: the refresh dialog is up (or forceRefresh already
    //                         reloaded the page); later cycles do nothing.
    //
    // One cycle = one PROBE, then exactly one verdict, taken only while still the latest live
    // cycle:
    //   PROBE     app-status on a fresh solara.control comm, up to 3 attempts of 2s with
    //             backoff (probeAppStatus). Only CONSISTENT failure is a verdict; a single
    //             late/lost reply is not.
    //   RESUME    started && viewMounted -> fetchAll() (same-instance hot reconnect).
    //   REPAIR    started && !viewMounted -> a previous rebuild tore the view down but never
    //             completed (socket drop mid-rebuild): the app is running server-side, so
    //             re-attach to its root container (rebuildView with reply.containerId).
    //   REMOUNT   !started && canRecover && clientVersion matches -> rebuildView(run): the
    //             server restores persisted state on its fresh kernel (§6.2).
    //   GIVE UP   otherwise -> fallbackToDialog(): needsRefresh + shutdownKernel. The ONLY
    //             place that shuts the kernel down or raises the dialog.
    //
    // Invariants:
    //   1. at most one cycle - the latest - takes a verdict and touches the UI state
    //      (remounting indicator, dialog); there is no in-flight boolean that can wedge -
    //      ownership is the generation number, and superseded work simply returns.
    //   2. a rebuild either completes to a mounted view (viewMounted = true) or leaves
    //      viewMounted == false, which the NEXT cycle detects and repairs; a rebuild hung on a
    //      lost reply can therefore never block recovery.
    //   3. the server half (kernel_context.initialize_virtual_kernel) generation-checks a
    //      reused context against the backend and supersedes it BEFORE wiring the websocket,
    //      so the probe always observes the post-supersede context.
    // =====================================================================================
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
            const generation = ++reconnectGeneration;
            const superseded = () => generation !== reconnectGeneration || kernel.connectionStatus !== 'connected';
            (async () => {
                if (app.$data.needsRefresh) {
                    // terminal: we already gave up
                    return;
                }
                const reply = await probeAppStatus(superseded);
                if (reply === null || superseded()) {
                    return;
                }
                solara.debug.lastRestore = reply.lastRestore || null;
                if (reply.started && viewMounted) {
                    // RESUME. Settle the indicator first: a previous rebuild may have completed
                    // its mount just as its socket dropped, leaving the overlay up.
                    app.$data.remounting = false;
                    await widgetManager.fetchAll();
                } else if (reply.started) {
                    // REPAIR (falls back to a plain REMOUNT when the server predates containerId)
                    await rebuildView(superseded, reply.containerId || null);
                } else if (reply.canRecover && reply.clientVersion === solara.clientVersion) {
                    // REMOUNT
                    await rebuildView(superseded, null);
                } else {
                    // GIVE UP
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
    await solaraMount(widgetManager, mountId, widgetModelId);
    viewMounted = true;
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
                widgetViews[mountId] = view;
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
