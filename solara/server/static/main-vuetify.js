
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
    let kernel = await solara.connectKernel(solara.rootPath + '/jupyter', kernelId)
    if (!kernel) {
        return;
    }
    const close_url = `${solara.rootPath}/_solara/api/close/${kernelId}?session_id=${kernel.clientId}`;
    let skipReconnectedCheck = true;
    kernel.statusChanged.connect(() => {
        app.$data.kernelBusy = kernel.status == 'busy';
    });

    window.addEventListener('solara.router', function (event) {
        app.$data.loadingPage = true;
    });
    kernel.statusChanged.connect(() => {
        // the first idle after a loadingPage == true (a router event)
        // will be used as indicator that the page is loaded
        if (app.$data.loadingPage && kernel.status == 'idle') {
            app.$data.loadingPage = false;
        }
    });


    kernel.connectionStatusChanged.connect((s) => {
        if (unloading) {
            // we don't want to show ui changes when hitting refresh
            return;
        }
        app.$data.connectionStatus = s.connectionStatus;
        if (s.connectionStatus == 'connected') {
            app.$data.wasConnected = true;
        }
        if (s.connectionStatus == 'connected' && !skipReconnectedCheck) {
            (async () => {
                if (app.$data.needsRefresh) {
                    // give up
                    return;
                }
                // if we are reconnected, we expected the app to be in a started
                // state. If it is not started, we will shutdown the kernel and
                // Recommend to refresh the page. This situation can happen if
                // we reconnect to a different node/worker, or when the server
                // was restarted.
                const status = await widgetManager.appStatus()
                if (!status.started) {
                    app.$data.needsRefresh = true;
                    await solara.shutdownKernel(kernel);
                } else {
                    await widgetManager.fetchAll();
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

    let widgetManager = new solara.WidgetManager(context, rendermime, settings);
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
