

function connectWatchdog() {
    var path = '';
    WSURL = 'ws://' + window.location.host
    var wsWatchdog = new WebSocket(WSURL + '/solara/watchdog/' + path);
    wsWatchdog.onopen = () => {
        console.log('connected with watchdog')
    }
    wsWatchdog.onmessage = (evt) => {
        var msg = JSON.parse(evt.data)
        if (msg.type == 'reload') {
            var timeout = 0;
            // if(msg.delay == 'long')
            //     timeout = 1000;
            setTimeout(() => {
                location.href = location.href;
            }, timeout)
        }
    }
    wsWatchdog.onclose = () => {
        timeout = 100
        console.log('disconnected watchdog, reconnecting in ', timeout / 1000, 'seconds')
        setTimeout(() => {
            connectWatchdog();
        }, timeout)
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
const COOKIE_KEY_CONTEXT_ID = 'solara-context-id'

// var app = new Vue({
//     vuetify: new Vuetify({
//         theme: { dark: false },
//     }),
//     el: '#app',
//     mounted() {
//         // document.querySelector('#app').removeAttribute("style");
//     },
//     data() {
//         return {
//             loading_text: "Loading page",
//             loadingPercentage: -1,
//             loading: true,
//             title: ""
//         }
//     }
// });

function websocket() {

};

function solaraMount(model_id) {
    // define("vue", [], () => Vue);
    // define("vuetify", [], { framework: app.$vuetify });
    console.log(document.cookie)
    cookies = getCookiesMap(document.cookie);
    const contextId = cookies[COOKIE_KEY_CONTEXT_ID]
    console.log('contextId', contextId)
    connectWatchdog()
    // var path = window.location.pathname.substr(14);
    console.log("will mount", model_id)
    // NOTE: this file is not transpiled, async/await is the only modern feature we use here
    require([window.voila_js_url || '/static/dist/voila.js'], function (voila) {
        // requirejs doesn't like to be passed an async function, so create one inside
        (async function () {
            var kernel = await voila.connectKernel('jupyter', null, websocket)
            if (!kernel) {
                return;
            }

            const context = {
                sessionContext: {
                    session: {
                        kernel,
                        kernelChanged: {
                            connect: () => { }
                        },
                    },
                    statusChanged: {
                        connect: () => { }
                    },
                    kernelChanged: {
                        connect: () => { }
                    },
                    connectionStatusChanged: {
                        connect: () => { }
                    },
                },
                saveState: {
                    connect: () => { }
                },
            };

            const settings = {
                saveState: false
            };

            const rendermime = new voila.RenderMimeRegistry({
                initialFactories: voila.extendedRendererFactories
            });

            var widgetManager = new voila.WidgetManager(context, rendermime, settings);

            async function init() {
                // it seems if we attach this to early, it will not be called
                const matches = document.cookie.match('\\b_xsrf=([^;]*)\\b');
                const xsrfToken = (matches && matches[1]) || '';
                const configData = JSON.parse(document.getElementById('jupyter-config-data').textContent);
                const baseUrl = 'jupyter';
                window.addEventListener('beforeunload', function (e) {
                    const data = new FormData();
                    data.append("_xsrf", xsrfToken);
                    window.navigator.sendBeacon(`${baseUrl}voila/api/shutdown/${kernel.id}`, data);
                    kernel.dispose();
                });
                await widgetManager.build_widgets();
                voila.renderMathJax();
                await Promise.all(Object.values(widgetManager._models)
                    .map(async (modelPromise) => {
                        const model = await modelPromise;
                        // console.log(model)
                        if (model.model_id == model_id) {
                            console.log("yeah, got it!", model_id)
                            const view = await widgetManager.create_view(model);
                            el = document.getElementById("content");
                            while (el.lastChild) {
                                el.removeChild(el.lastChild);
                            }
                            // el.appendChild(view.el);
                            requirejs(['@jupyter-widgets/base'], widgets =>
                                //   widgets.JupyterPhosphorWidget.attach(widgetView.pWidget, this.$el)
                                widgets.JupyterPhosphorWidget.attach(view.pWidget, el)
                            );

                            console.log('el')
                            // provideWidget(mountId, view);
                        }
                    }));

            }

            if (document.readyState === 'complete') {
                init()
            } else {
                window.addEventListener('load', init);
            }
        })()
    });

}
