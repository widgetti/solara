// webworker.js

// synchronously loads pyodide
importScripts("https://cdn.jsdelivr.net/pyodide/v0.20.0/full/pyodide.js");


async function loadSolara() {
    self.pyodide = await loadPyodide()
    await self.pyodide.loadPackage('micropip');
    await self.pyodide.runPythonAsync(`
    from pyodide.http import pyfetch
    response = await pyfetch("/static/solara_bootstrap.py")
    with open("solara_bootstrap.py", "wb") as f:
        f.write(await response.bytes())
    import solara_bootstrap
    await solara_bootstrap.main()
    import solara.server.pyodide`)
    self.model_id = self.pyodide.runPython('import solara.server.pyodide as p; p.start("solara.website.pages:Page")')
    self.postMessage({ 'type': 'opened' })
}

solara = loadSolara()

// this will be called from solara.server.pyodide
self.sendToPage = function (msg) {
    // console.log('send to page', msg)
    msg = { 'type': 'send', 'value': msg }
    // forward to the page
    self.postMessage(msg)
}

// when we get a msg from the page
self.onmessage = async (event) => {
    // console.log("send to solara", event)
    // make sure the bootstrapping ran
    solara_ = await solara;
    solaraPyodide = self.pyodide.runPython('import solara.server.pyodide as p; p');
    msg = event.data
    if (msg.type == 'send') {
        await solaraPyodide.processKernelMessage(event.data['value'])
    }
};
