# Embedding in existing websites

Solara can be embedded into existing websites. Although it is technically possible to embed a Solara app into an existing webpage, we currently support embedding primarily via iframes.


## Embed via iframe

Here we demonstrate how to embed Solara into an existing webpage via an iframe. Let's start by creating a simple HTML page (here we choose the filename embed.html):

```html
<html>
<body>
    <h1>This is on the main page</h1>
    <iframe src="http://localhost:8765" width="100%" height="100%"></iframe>
</body>
</html>
```

Now, start an http server (in this example we use the standard Python http server):
```bash
$ python -m http.server
Serving HTTP on :: port 8000 (http://[::]:8000/) ...
```

Additionally, start the Solara server:

```bash
$ solara run my-solara-app.py
Solara server is starting at http://localhost:8765
```

Ensure the port number matches that of the iframe in `embed.html`. Now open `http://localhost:8000/embed.html` in your browser, and you should see the Solara app embedded in the page.

If you do not see your app, you can open the browser developer tools in your browser and look for errors in the console. If you use the Brave browser, you might want to disable the Brave shields for your local server.

### Security considerations

Solara uses a cookie to implement sessions. To support cookies settings in an iframe, we set the session cookie using `Secure`, and `SameSite=Strict`. See [https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#restrict_access_to_cookies](MDN) for more details. This means that we can only support loading via iframes via https or localhost.


## Embed into an existing page

If embedding into an iframe does not suit your needs (for example, dialogs not being fullscreen), [please contact us](/docs/contact) and we can discuss other options.
