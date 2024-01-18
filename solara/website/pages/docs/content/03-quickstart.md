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

Put the following Python snippet in a file (we suggest `sol.py`), or put it in a Jupyter notebook cell:

```solara
import solara

# Declare reactive variables at the top level. Components using these variables
# will be re-executed when their values change.
sentence = solara.reactive("Solara makes our team more productive.")
word_limit = solara.reactive(10)


@solara.component
def Page():
    # Calculate word_count within the component to ensure re-execution when reactive variables change.
    word_count = len(sentence.value.split())

    solara.SliderInt("Word limit", value=word_limit, min=2, max=20)
    solara.InputText(label="Your sentence", value=sentence, continuous_update=True)

    # Display messages based on the current word count and word limit.
    if word_count >= int(word_limit.value):
        solara.Error(f"With {word_count} words, you passed the word limit of {word_limit.value}.")
    elif word_count >= int(0.8 * word_limit.value):
        solara.Warning(f"With {word_count} words, you are close to the word limit of {word_limit.value}.")
    else:
        solara.Success("Great short writing!")


# The following line is required only when running the code in a Jupyter notebook:
Page()
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

<img src="https://dxhl76zpt6fap.cloudfront.net/public/quickstart-notebook.webp" alt="Markdown Monster icon" style="border: 1px solid #ccc;" />

In case you forgot how to start a notebook server:

    $ jupyter notebook

Or the more modern Jupyter lab:

    $ jupyter lab
