# Voilà

[Voilà](https://voila.readthedocs.io/) allows you to convert a Jupyter Notebook into an interactive dashboard that allows you to share your work with others.

Voilà is Jupyter notebook focused, meaning that it will render all output from your notebook. Using [`voila-vuetify`](https://github.com/voila-dashboards/voila-vuetify) Voilà allows for a more app like experience, showing only the output you want.

Voilà, together with `voila-vuetify` is an alternative to [Solara server](./solara-server). The most significant difference is that Voilà will start one kernel/process per page request, while [Solara server](./solara-server) can serve many more users from a single process. Sharing the same process means Solara apps can share memory among users (e.g. a large dataset), which will usually lead to better performance and less resource usage.
