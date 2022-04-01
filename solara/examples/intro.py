import react_ipywidgets as react
from react_ipywidgets import ipywidgets as w


@react.component
def Markdown(md_text: str):
    import markdown

    html = markdown.markdown(md_text)
    return w.HTML(value=html)


# app =
