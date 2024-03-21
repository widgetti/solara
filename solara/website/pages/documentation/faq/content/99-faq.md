
# FAQ

## I am not interested in the server, I'm happy with Jupyter/Voila, what's in it for me?

That means you simply do not use or install the server component, just use the Reacton components and run it with Voila.

## Is the Solara server better than Voilà?

No, they are different, and there are situations where I would recommend Voila instead of Solara.

If your app is compute-heavy, and a lot of the compute is happening in pure Python, the GIL (Global Interpreter Lock) can become a bottleneck with Solara, and Voila might give you better performance per client.

If you have a lot of users with short sessions, Solara spares you from having to start up a kernel for each request. Since Solara can use multiple workers in the near future, you can still scale up using multiple processes. Voila will have one process per user, while Solara can share a process with many users.


## Can Solara run a normal Python script?

Yes, this is the preferred way of using Solara. You edit a Python script, save it, Solara will detect the file change and reload the page in your browser (no interaction is needed).

```bash
$ solara myapp.py
Solara server is starting at http://localhost:8766
... file change detected ...
(server refreshes, your page will reload)

```

## Can Solara run from a Python package/module?

Over time, when your application becomes larger, you probably want to structure your application into a Python package. Instead of a filename, you pass in the package name on the command line

```bash
$ solara mystartup.killerapp --dev
....
```

## Can Solara run Jupyter notebook?

Yes, Solara will execute each cell, and after that will look for a variable or component called `Page`, like with a normal script. All other output, Markdown or other types of cells will be ignored.



## Can I use Solara in my existing FastAPI/Starlette/Flask server?

Yes, take a look at the `solara.server.starlette`  and `solara.server.fastapi` and `solara.server.flask` module. The usage will change over time, so read the source and be ready to change this in the future. We do plan to provide a stable API for this in the future.


## How to fix: inotify watch limit reached?

Add the line

    fs.inotify.max_user_watches=524288

To your /etc/sysctl.conf file, and run `sudo sysctl -p.`

Or if you are using visual studio code, please read: https://code.visualstudio.com/docs/setup/linux#_visual-studio-code-is-unable-to-watch-for-file-changes-in-this-large-workspace-error-enospc


## How can I recognize if I run in Solara, Voila or Jupyter Notebook/Lab

Voila and Solara set the following environment variables (based on the CGI spec):

   * SERVER_SOFTWARE
      * Solara: e.g. 'solara/1.2.3'
      * Voila: e.g. 'voila/1.2.3'
   * SERVER_PORT (e.g. '8765')
   * SERVER_NAME (e.g. 'killerapp.com')
   * SCRIPT_NAME (only Voila, e.g. 'voila/render/notebook.ipynb')
   * PATH_TRANSLATED (only Solara e.g. '/mnt/someapp/app.py')

Jupyter Notebook/Lab/Server do not set these variables. With this information,
it should be possible to recognize in which environment you are running in.
