# Quickstart

This 1-minute quickstart will get you to:

   * Solara install.
   * Write your first Solara script.
   * Run your script using Solara server.
   * (Optional) Reuse your code in the Jupyter notebook.

## You should know

This quickstart will assume:

  * You have successfully installed Solara

If not, please follow the [Installation instructions](/docs/installing).


## First script

Put the following content in a file, say `sol.py`:

```solara
import solara

@solara.component
def Page():
    sentence, set_sentence = solara.use_state("Solara makes our team more productive.")
    word_limit, set_word_limit = solara.use_state(10)
    word_count = len(sentence.split())

    with solara.VBox() as main:
        solara.SliderInt("Word limit", value=word_limit, on_value=set_word_limit, min=2, max=20)
        solara.InputText(label="Your sentence", value=sentence, on_value=set_sentence,
                         continuous_update=True)

        if word_count >= int(word_limit):
            solara.Error(f"With {word_count} words, you passed the word limit of {word_limit}.")
        elif word_count >= int(0.8 * word_limit):
            solara.Warning(f"With {word_count} words, you are close to the word limit of {word_limit}.")
        else:
            solara.Success("Great short writing!")
    return main
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
