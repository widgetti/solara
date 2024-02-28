**A Pure Python, React-style Framework for Scaling Your Jupyter and Web Apps**

[![solara logo](https://solara.dev/static/assets/images/logo.svg)](https://solara.dev)

Come chat with us on [Discord](https://discord.solara.dev) to ask questions or share your thoughts or creations!

[![Discord Shield](https://discordapp.com/api/guilds/1106593685241614489/widget.png?style=banner2)](https://discord.solara.dev)



## Introducing Solara

While there are many Python web frameworks out there, most are designed for small data apps or use paradigms unproven for larger scale. Code organization, reusability, and state tend to suffer as apps grow in complexity, resulting in either spaghetti code or offloading to a React application.

Solara addresses this gap. Using a React-like API, we don't need to worry about scalability. React has already proven its ability to support the world's largest web apps.

Solara uses a pure Python implementation of React (Reacton), creating ipywidget-based applications. These apps work both inside the Jupyter Notebook and as standalone web apps with frameworks like FastAPI. This paradigm enables component-based code and incredibly simple state management.

By building on top of ipywidgets, we automatically leverage an existing ecosystem of widgets and run on many platforms, including JupyterLab, Jupyter Notebook, Voilà, Google Colab, DataBricks, JetBrains Datalore, and more.

We care about developer experience. Solara will give your hot code reloading and type hints for faster development.

## Installation

Run:
```
pip install solara
```

Or follow the [Installation instructions](https://solara.dev/docs/installing) for more detailed instructions.

## First script

Put the following Python snippet in a file (we suggest `sol.py`), or put it in a Jupyter notebook cell:

```python
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

Run from the command line in the same directory where you put your file (`sol.py`):

```bash
$ solara run sol.py
Solara server is starting at http://localhost:8765
```

Or copy-paste this to a Jupyter notebook cell and execute it (the `Page()` expression at the end
will cause it to automatically render the component in the notebook).

See this snippet run live at https://solara.dev/docs/quickstart

## Demo

The following demo app can be used to explore a dataset (buildin or upload yourself) using
a scatter plot. The plot can be interacted with to filter the dataset, and the filtered dataset can
be downloaded.

 * [Source code](https://github.com/widgetti/solara/blob/master/solara/website/pages/apps/scatter.py)

### Running in solara-server

The solara server is build on top of Starlette/FastAPI and runs standalone. Ideal for production use.

![fastapi](https://global.discourse-cdn.com/standard11/uploads/jupyter/original/2X/9/9442fc70e2a1fcd201f4f900fa073698a1f8c937.gif)


### Running in Jupyter

By building on top of ipywidgets, we automatically leverage an existing ecosystem of widgets and run on many platforms, including JupyterLab, Jupyter Notebook, Voilà, Google Colab, DataBricks, JetBrains Datalore, and more. This means our app can also run in Jupyter:

![jupyter](https://global.discourse-cdn.com/standard11/uploads/jupyter/original/2X/8/8bc875c0c3845ae077168575a4f8a49cf1b35bc6.gif)

## Resources

Visit our main website or jump directly to the introduction

[![Introduction](https://dabuttonfactory.com/button.png?t=Introduction&f=Open+Sans-Bold&ts=20&tc=fff&hp=45&vp=12&c=8&bgt=unicolored&bgc=f19f41)](https://solara.dev/docs)
[![Quickstart](https://dabuttonfactory.com/button.png?t=Quickstart&f=Open+Sans-Bold&ts=20&tc=fff&hp=45&vp=12&c=8&bgt=unicolored&bgc=f19f41)](https://solara.dev/docs/quickstart)

*Note that the solara.dev website is created using Solara*
