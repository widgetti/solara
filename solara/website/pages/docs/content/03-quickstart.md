# Quickstart

This 1-minute quickstart will get you to:

   * Install Solara.
   * Write your first Solara script.
   * Run your script using Solara server.
   * (Optional) Reuse your code in the Jupyter notebook.

If you are an existing ipywidget user and do not want to learn the component based method, you might want to skip the quickstart and directly go to the [IPywidgets user tutorial](/docs/tutorial/ipywidgets).

## Installation


Run `pip install solara`, or follow the [Installation instructions](/docs/installing) for more detailed instructions.


## First script

Put the following Python script in a file, we suggest `sol.py`:

```solara
import solara

sentence = solara.reactive("Solara makes our team more productive.")
word_limit = solara.reactive(10)


@solara.component
def Page():
    word_count = len(sentence.value.split())

    solara.SliderInt("Word limit", value=word_limit, min=2, max=20)
    solara.InputText(label="Your sentence", value=sentence, continuous_update=True)

    if word_count >= int(word_limit.value):
        solara.Error(f"With {word_count} words, you passed the word limit of {word_limit.value}.")
    elif word_count >= int(0.8 * word_limit.value):
        solara.Warning(f"With {word_count} words, you are close to the word limit of {word_limit.value}.")
    else:
        solara.Success("Great short writing!")


# In a Jupyter notebook, put this at the end of your cell:
# Page()
```

Yes, the above example is running live on the Solara documentation web server. If you change the slider the output updates.

## Run the script using Solara server

Run from the command line in the same directory where you put your file (`sol.py`):

```bash
$ solara run sol.py
Solara server is starting at http://localhost:8765
```

If you open the URL in your browser ([http://localhost:8765](http://localhost:8765)), you should see the same graph in your browser, now running on your computer.

## Reuse your code in the Jupyter notebook.

From Jupyter Notebook (classic) or Jupyter Lab, navigate to the same directory as `sol.py`. Enter the following code in a notebook cell:

```python
from sol import Page
display(Page())
```

You should see the following output:

<img src="/static/public/quickstart-notebook.png" alt="Markdown Monster icon" style="border: 1px solid #ccc;" />

In case you forgot how to start a notebook server:

    $ jupyter notebook

Or the more modern Jupyter lab:

    $ jupyter lab
