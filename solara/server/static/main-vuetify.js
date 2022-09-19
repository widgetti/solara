Vue.use(Vuetify);

Vue.component('jupyter-widget-mount-point', {
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
        if (this.renderFn) {
            /* workaround for v-menu click */
            if (!this.elem) {
                this.elem = this.renderFn(createElement);
            }
            return this.elem;
        }
        return createElement('div', this.$slots.default ||
            [createElement('v-chip', `[${this.mountId}]`)]);
    }
});

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


class WebSocketRedirectWebWorker {
    // redirects to webworker
    constructor(url) {
        console.log('connect url intercepted', url)
        function make_default(name) {
            return () => {
                console.log("default ", name)
            }
        }
        this.onopen = make_default('onopen')
        this.onclose = make_default('onclose')
        this.onmessage = make_default('onmessage')
        setTimeout(() => this.start(), 10)
    }
    send(msg) {
        // console.log('send msg', msg)
        solaraWorker.postMessage({ 'type': 'send', 'value': msg })
    }
    start() {
        solaraWorker.addEventListener('message', async (event) => {
            let msg = event.data
            // console.log('on msg', msg)
            if (msg.type == 'opened') {
                this.onopen()
            }
            if (msg.type == 'send') {
                this.onmessage({ data: msg.value })
            }
        });
        // solaraWorker.postMessage({ 'type': 'open' })
    }
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
    define("vuetify", [], { framework: app.$vuetify });
    cookies = getCookiesMap(document.cookie);
    uuid = generateUuid()
    window.addEventListener('beforeunload', function (e) {
        kernel.dispose()
        window.navigator.sendBeacon(close_url);
    });

    if (for_pyodide) {
        options = { WebSocket: WebSocketRedirectWebWorker }
    } else {
        options = {}
    }
    let kernel = await solara.connectKernel('jupyter', uuid, options)
    if (!kernel) {
        return;
    }
    const close_url = document.baseURI + '_solara/api/close/' + kernel.clientId;
    let skipReconnectedCheck = true;
    kernel.statusChanged.connect(() => {
        app.$data.kernelBusy = kernel.status == 'busy';
    });
    kernel.connectionStatusChanged.connect((s) => {
        app.$data.connectionStatus = s.connectionStatus;
        if (s.connectionStatus == 'connected') {
            app.$data.wasConnected = true;
        }
        if (s.connectionStatus == 'connected' && !skipReconnectedCheck) {
            (async () => {
                let ok = await widgetManager.check()
                if (!ok) {
                    app.$data.needsRefresh = true
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

    const rendermime = new solara.RenderMimeRegistry({
        initialFactories: solara.extendedRendererFactories
    });

    let widgetManager = new solara.WidgetManager(context, rendermime, settings);
    // it seems if we attach this to early, it will not be called
    app.$data.loading_text = 'Loading app';
    const widgetId = await widgetManager.run(appName);
    await solaraMount(widgetManager, mountId || 'content', widgetId);
    skipReconnectedCheck = false;
    solara.renderMathJax();
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
