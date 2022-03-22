# What is Solara?


<img src="https://user-images.githubusercontent.com/1765949/159178788-2c20214d-d4fe-42cd-a28e-7097ce37c904.svg" height="200px"/>

## What is it?

If you only care about using Solara from the Jupyter notebook (classic or lab) or Voila, it is:

   * A set of composable components build on [React-IPywidgets](https://github.com/widgetti/react-ipywidgets) (e.g., Image, Markdown, FileBrowser, etcetera) to get that 'all batteries included' feeling.


If you also want to develop and deploy a more extensive application and prefer not to program in a Jupyter notebook, or care about scaling your application, Solara is also:

   * An application server to make development easier:
       * Auto reloading refreshes the page when you save your script or Jupyter notebook.
       * Your app state is restored after reload/restart: All tabs, checkboxes, etcetera will be as you set them.
   * An application server that:
      * Runs on Starlette (used in FastAPI).
      * Executes:
         * Python scripts
         * Python modules/packages
         * Jupyter notebooks
   * An alternative for Voila, for when:
     * You only need to display widgets
     * One kernel/process per request is becoming a bottleneck/cost issue.
     * Only care about using Python (e.g., not Julia, R)
     * Are ok, or even prefers, to have your application code run in the same process as your web server (e.g., FastAPI, Starlette)

Read more at [GitHub](http://github.com/widgetti/solara/)
