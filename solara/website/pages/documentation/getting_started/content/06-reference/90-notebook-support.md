---
title: Using Solara within notebooks
description: Solara can be used to generate an interactive app directly using your notebook file by running just one command.
---
# Notebook support

We also support notebooks, simply assign to the `Page` variable in a code cell, save your notebook, and run `$ solara run myapp.ipynb`. If you widget or component is called differently, run like `$ solara run myapp.ipynb:myobject.nested_widget`.
