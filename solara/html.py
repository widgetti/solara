from pathlib import Path

import ipyvue
import requests
from reacton.utils import implements

import solara.util

MAX_LINE_LENGTH = 160 - 8

HERE = Path(__file__).parent
html_url = "https://raw.githubusercontent.com/jozo/all-html-elements-and-attributes/master/html-elements-attributes.json"
template = """

def _{Name}(style: Union[str, Dict[str, str], None] = None, classes: List[str] = [], children: List[Union[str, solara.Element]] = [], {args}):
    ...

@implements(_{Name})
def {Name}(**kwargs):
    return _HtmlImpl(tag="{name}", attributes=kwargs)
"""


def _HtmlImpl(tag, attributes):
    style_ = None
    class_ = None
    if "style" in attributes:
        style_ = solara.util._flatten_style(attributes.pop("style"))
    if "classes" in attributes:
        class_ = solara.util._combine_classes(attributes.pop("classes"))
    return ipyvue.Html.element(tag=tag, attributes=attributes, style_=style_, class_=class_)


def main():
    data = requests.get(html_url).json()
    common_attributes = data.pop("*")
    path = HERE / "html.py"
    code = path.read_text()
    marker = ":edoc detareneg #"[::-1]  # reverse string otherwise it matches itself
    index = code.index(marker) + len(marker) + 1
    code = code[:index]

    def translate(attribute_name):
        # keywords like style and class get suffixed with _
        attribute_name = attribute_name.replace("-", "_")
        if attribute_name in ("for", "async"):
            return attribute_name + "_"
        return attribute_name

    for name, attributes in data.items():
        # print(name, attributes)
        Name = name.title()
        args = ", ".join([f"{translate(key)}=None" for key in common_attributes + attributes if ("*" not in key and key not in ["style", "class"])])
        snippet = template.format(name=name, args=args, Name=Name)
        code += snippet
    code += "\n"
    import black

    mode = black.Mode(line_length=MAX_LINE_LENGTH)
    code = black.format_file_contents(code, fast=False, mode=mode)
    # make sure the code is valid
    exec(code, {"__name__": "__notmain__", "__file__": str(path)})
    path.write_text(code)


if __name__ == "__main__":
    main()


# generated code:


def _A(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    download=None,
    href=None,
    hreflang=None,
    media=None,
    ping=None,
    referrerpolicy=None,
    rel=None,
    shape=None,
    target=None,
    children=[],
):
    ...


@implements(_A)
def A(**kwargs):
    return _HtmlImpl(tag="a", attributes=kwargs)


def _Abbr(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Abbr)
def Abbr(**kwargs):
    return _HtmlImpl(tag="abbr", attributes=kwargs)


def _Acronym(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Acronym)
def Acronym(**kwargs):
    return _HtmlImpl(tag="acronym", attributes=kwargs)


def _Address(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Address)
def Address(**kwargs):
    return _HtmlImpl(tag="address", attributes=kwargs)


def _Applet(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    alt=None,
    code=None,
    codebase=None,
    children=[],
):
    ...


@implements(_Applet)
def Applet(**kwargs):
    return _HtmlImpl(tag="applet", attributes=kwargs)


def _Area(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    alt=None,
    coords=None,
    download=None,
    href=None,
    hreflang=None,
    media=None,
    ping=None,
    referrerpolicy=None,
    rel=None,
    shape=None,
    target=None,
    children=[],
):
    ...


@implements(_Area)
def Area(**kwargs):
    return _HtmlImpl(tag="area", attributes=kwargs)


def _Article(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Article)
def Article(**kwargs):
    return _HtmlImpl(tag="article", attributes=kwargs)


def _Aside(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Aside)
def Aside(**kwargs):
    return _HtmlImpl(tag="aside", attributes=kwargs)


def _Audio(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    autoplay=None,
    buffered=None,
    controls=None,
    crossorigin=None,
    loop=None,
    muted=None,
    preload=None,
    src=None,
    children=[],
):
    ...


@implements(_Audio)
def Audio(**kwargs):
    return _HtmlImpl(tag="audio", attributes=kwargs)


def _B(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_B)
def B(**kwargs):
    return _HtmlImpl(tag="b", attributes=kwargs)


def _Base(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    href=None,
    target=None,
    children=[],
):
    ...


@implements(_Base)
def Base(**kwargs):
    return _HtmlImpl(tag="base", attributes=kwargs)


def _Basefont(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    color=None,
    children=[],
):
    ...


@implements(_Basefont)
def Basefont(**kwargs):
    return _HtmlImpl(tag="basefont", attributes=kwargs)


def _Bdi(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Bdi)
def Bdi(**kwargs):
    return _HtmlImpl(tag="bdi", attributes=kwargs)


def _Bdo(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Bdo)
def Bdo(**kwargs):
    return _HtmlImpl(tag="bdo", attributes=kwargs)


def _Bgsound(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    loop=None,
    children=[],
):
    ...


@implements(_Bgsound)
def Bgsound(**kwargs):
    return _HtmlImpl(tag="bgsound", attributes=kwargs)


def _Big(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Big)
def Big(**kwargs):
    return _HtmlImpl(tag="big", attributes=kwargs)


def _Blink(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Blink)
def Blink(**kwargs):
    return _HtmlImpl(tag="blink", attributes=kwargs)


def _Blockquote(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    cite=None,
    children=[],
):
    ...


@implements(_Blockquote)
def Blockquote(**kwargs):
    return _HtmlImpl(tag="blockquote", attributes=kwargs)


def _Body(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    background=None,
    bgcolor=None,
    children=[],
):
    ...


@implements(_Body)
def Body(**kwargs):
    return _HtmlImpl(tag="body", attributes=kwargs)


def _Br(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Br)
def Br(**kwargs):
    return _HtmlImpl(tag="br", attributes=kwargs)


def _Button(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    autofocus=None,
    disabled=None,
    form=None,
    formaction=None,
    formenctype=None,
    formmethod=None,
    formnovalidate=None,
    formtarget=None,
    name=None,
    type=None,
    value=None,
    children=[],
):
    ...


@implements(_Button)
def Button(**kwargs):
    return _HtmlImpl(tag="button", attributes=kwargs)


def _Canvas(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    height=None,
    width=None,
    children=[],
):
    ...


@implements(_Canvas)
def Canvas(**kwargs):
    return _HtmlImpl(tag="canvas", attributes=kwargs)


def _Caption(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    children=[],
):
    ...


@implements(_Caption)
def Caption(**kwargs):
    return _HtmlImpl(tag="caption", attributes=kwargs)


def _Center(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Center)
def Center(**kwargs):
    return _HtmlImpl(tag="center", attributes=kwargs)


def _Cite(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Cite)
def Cite(**kwargs):
    return _HtmlImpl(tag="cite", attributes=kwargs)


def _Code(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Code)
def Code(**kwargs):
    return _HtmlImpl(tag="code", attributes=kwargs)


def _Col(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    bgcolor=None,
    span=None,
    children=[],
):
    ...


@implements(_Col)
def Col(**kwargs):
    return _HtmlImpl(tag="col", attributes=kwargs)


def _Colgroup(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    bgcolor=None,
    span=None,
    children=[],
):
    ...


@implements(_Colgroup)
def Colgroup(**kwargs):
    return _HtmlImpl(tag="colgroup", attributes=kwargs)


def _Command(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    checked=None,
    disabled=None,
    icon=None,
    radiogroup=None,
    type=None,
    children=[],
):
    ...


@implements(_Command)
def Command(**kwargs):
    return _HtmlImpl(tag="command", attributes=kwargs)


def _Content(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Content)
def Content(**kwargs):
    return _HtmlImpl(tag="content", attributes=kwargs)


def _Contenteditable(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    enterkeyhint=None,
    inputmode=None,
    children=[],
):
    ...


@implements(_Contenteditable)
def Contenteditable(**kwargs):
    return _HtmlImpl(tag="contenteditable", attributes=kwargs)


def _Data(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    value=None,
    children=[],
):
    ...


@implements(_Data)
def Data(**kwargs):
    return _HtmlImpl(tag="data", attributes=kwargs)


def _Datalist(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Datalist)
def Datalist(**kwargs):
    return _HtmlImpl(tag="datalist", attributes=kwargs)


def _Dd(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Dd)
def Dd(**kwargs):
    return _HtmlImpl(tag="dd", attributes=kwargs)


def _Del(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    cite=None,
    datetime=None,
    children=[],
):
    ...


@implements(_Del)
def Del(**kwargs):
    return _HtmlImpl(tag="del", attributes=kwargs)


def _Details(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    open=None,
    children=[],
):
    ...


@implements(_Details)
def Details(**kwargs):
    return _HtmlImpl(tag="details", attributes=kwargs)


def _Dfn(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Dfn)
def Dfn(**kwargs):
    return _HtmlImpl(tag="dfn", attributes=kwargs)


def _Dialog(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    open=None,
    children=[],
):
    ...


@implements(_Dialog)
def Dialog(**kwargs):
    return _HtmlImpl(tag="dialog", attributes=kwargs)


def _Dir(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Dir)
def Dir(**kwargs):
    return _HtmlImpl(tag="dir", attributes=kwargs)


def _Div(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Div)
def Div(**kwargs):
    return _HtmlImpl(tag="div", attributes=kwargs)


def _Dl(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Dl)
def Dl(**kwargs):
    return _HtmlImpl(tag="dl", attributes=kwargs)


def _Dt(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Dt)
def Dt(**kwargs):
    return _HtmlImpl(tag="dt", attributes=kwargs)


def _Em(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Em)
def Em(**kwargs):
    return _HtmlImpl(tag="em", attributes=kwargs)


def _Embed(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    height=None,
    src=None,
    type=None,
    width=None,
    children=[],
):
    ...


@implements(_Embed)
def Embed(**kwargs):
    return _HtmlImpl(tag="embed", attributes=kwargs)


def _Fieldset(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    disabled=None,
    form=None,
    name=None,
    children=[],
):
    ...


@implements(_Fieldset)
def Fieldset(**kwargs):
    return _HtmlImpl(tag="fieldset", attributes=kwargs)


def _Figcaption(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Figcaption)
def Figcaption(**kwargs):
    return _HtmlImpl(tag="figcaption", attributes=kwargs)


def _Figure(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Figure)
def Figure(**kwargs):
    return _HtmlImpl(tag="figure", attributes=kwargs)


def _Font(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    color=None,
    children=[],
):
    ...


@implements(_Font)
def Font(**kwargs):
    return _HtmlImpl(tag="font", attributes=kwargs)


def _Footer(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Footer)
def Footer(**kwargs):
    return _HtmlImpl(tag="footer", attributes=kwargs)


def _Form(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    accept=None,
    accept_charset=None,
    action=None,
    autocomplete=None,
    enctype=None,
    method=None,
    name=None,
    novalidate=None,
    target=None,
    children=[],
):
    ...


@implements(_Form)
def Form(**kwargs):
    return _HtmlImpl(tag="form", attributes=kwargs)


def _Frame(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Frame)
def Frame(**kwargs):
    return _HtmlImpl(tag="frame", attributes=kwargs)


def _Frameset(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Frameset)
def Frameset(**kwargs):
    return _HtmlImpl(tag="frameset", attributes=kwargs)


def _H1(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_H1)
def H1(**kwargs):
    return _HtmlImpl(tag="h1", attributes=kwargs)


def _H2(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_H2)
def H2(**kwargs):
    return _HtmlImpl(tag="h2", attributes=kwargs)


def _H3(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_H3)
def H3(**kwargs):
    return _HtmlImpl(tag="h3", attributes=kwargs)


def _H4(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_H4)
def H4(**kwargs):
    return _HtmlImpl(tag="h4", attributes=kwargs)


def _H5(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_H5)
def H5(**kwargs):
    return _HtmlImpl(tag="h5", attributes=kwargs)


def _H6(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_H6)
def H6(**kwargs):
    return _HtmlImpl(tag="h6", attributes=kwargs)


def _Head(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Head)
def Head(**kwargs):
    return _HtmlImpl(tag="head", attributes=kwargs)


def _Header(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Header)
def Header(**kwargs):
    return _HtmlImpl(tag="header", attributes=kwargs)


def _Hgroup(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Hgroup)
def Hgroup(**kwargs):
    return _HtmlImpl(tag="hgroup", attributes=kwargs)


def _Hr(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    color=None,
    children=[],
):
    ...


@implements(_Hr)
def Hr(**kwargs):
    return _HtmlImpl(tag="hr", attributes=kwargs)


def _Html(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    manifest=None,
    children=[],
):
    ...


@implements(_Html)
def Html(**kwargs):
    return _HtmlImpl(tag="html", attributes=kwargs)


def _I(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_I)
def I(**kwargs):
    return _HtmlImpl(tag="i", attributes=kwargs)


def _Iframe(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    allow=None,
    csp=None,
    height=None,
    importance=None,
    loading=None,
    name=None,
    referrerpolicy=None,
    sandbox=None,
    src=None,
    srcdoc=None,
    width=None,
    children=[],
):
    ...


@implements(_Iframe)
def Iframe(**kwargs):
    return _HtmlImpl(tag="iframe", attributes=kwargs)


def _Image(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Image)
def Image(**kwargs):
    return _HtmlImpl(tag="image", attributes=kwargs)


def _Img(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    alt=None,
    border=None,
    crossorigin=None,
    decoding=None,
    height=None,
    importance=None,
    intrinsicsize=None,
    ismap=None,
    loading=None,
    referrerpolicy=None,
    sizes=None,
    src=None,
    srcset=None,
    usemap=None,
    width=None,
    children=[],
):
    ...


@implements(_Img)
def Img(**kwargs):
    return _HtmlImpl(tag="img", attributes=kwargs)


def _Input(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    accept=None,
    alt=None,
    autocomplete=None,
    autofocus=None,
    capture=None,
    checked=None,
    dirname=None,
    disabled=None,
    form=None,
    formaction=None,
    formenctype=None,
    formmethod=None,
    formnovalidate=None,
    formtarget=None,
    height=None,
    list=None,
    max=None,
    maxlength=None,
    minlength=None,
    min=None,
    multiple=None,
    name=None,
    pattern=None,
    placeholder=None,
    readonly=None,
    required=None,
    size=None,
    src=None,
    step=None,
    type=None,
    usemap=None,
    value=None,
    width=None,
    children=[],
):
    ...


@implements(_Input)
def Input(**kwargs):
    return _HtmlImpl(tag="input", attributes=kwargs)


def _Ins(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    cite=None,
    datetime=None,
    children=[],
):
    ...


@implements(_Ins)
def Ins(**kwargs):
    return _HtmlImpl(tag="ins", attributes=kwargs)


def _Kbd(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Kbd)
def Kbd(**kwargs):
    return _HtmlImpl(tag="kbd", attributes=kwargs)


def _Keygen(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    autofocus=None,
    challenge=None,
    disabled=None,
    form=None,
    keytype=None,
    name=None,
    children=[],
):
    ...


@implements(_Keygen)
def Keygen(**kwargs):
    return _HtmlImpl(tag="keygen", attributes=kwargs)


def _Label(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    for_=None,
    form=None,
    children=[],
):
    ...


@implements(_Label)
def Label(**kwargs):
    return _HtmlImpl(tag="label", attributes=kwargs)


def _Legend(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Legend)
def Legend(**kwargs):
    return _HtmlImpl(tag="legend", attributes=kwargs)


def _Li(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    value=None,
    children=[],
):
    ...


@implements(_Li)
def Li(**kwargs):
    return _HtmlImpl(tag="li", attributes=kwargs)


def _Link(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    crossorigin=None,
    href=None,
    hreflang=None,
    importance=None,
    integrity=None,
    media=None,
    referrerpolicy=None,
    rel=None,
    sizes=None,
    type=None,
    children=[],
):
    ...


@implements(_Link)
def Link(**kwargs):
    return _HtmlImpl(tag="link", attributes=kwargs)


def _Main(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Main)
def Main(**kwargs):
    return _HtmlImpl(tag="main", attributes=kwargs)


def _Map(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    name=None,
    children=[],
):
    ...


@implements(_Map)
def Map(**kwargs):
    return _HtmlImpl(tag="map", attributes=kwargs)


def _Mark(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Mark)
def Mark(**kwargs):
    return _HtmlImpl(tag="mark", attributes=kwargs)


def _Marquee(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    bgcolor=None,
    loop=None,
    children=[],
):
    ...


@implements(_Marquee)
def Marquee(**kwargs):
    return _HtmlImpl(tag="marquee", attributes=kwargs)


def _Math(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Math)
def Math(**kwargs):
    return _HtmlImpl(tag="math", attributes=kwargs)


def _Menu(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    type=None,
    children=[],
):
    ...


@implements(_Menu)
def Menu(**kwargs):
    return _HtmlImpl(tag="menu", attributes=kwargs)


def _Menuitem(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Menuitem)
def Menuitem(**kwargs):
    return _HtmlImpl(tag="menuitem", attributes=kwargs)


def _Meta(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    charset=None,
    content=None,
    http_equiv=None,
    name=None,
    children=[],
):
    ...


@implements(_Meta)
def Meta(**kwargs):
    return _HtmlImpl(tag="meta", attributes=kwargs)


def _Meter(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    form=None,
    high=None,
    low=None,
    max=None,
    min=None,
    optimum=None,
    value=None,
    children=[],
):
    ...


@implements(_Meter)
def Meter(**kwargs):
    return _HtmlImpl(tag="meter", attributes=kwargs)


def _Nav(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Nav)
def Nav(**kwargs):
    return _HtmlImpl(tag="nav", attributes=kwargs)


def _Nobr(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Nobr)
def Nobr(**kwargs):
    return _HtmlImpl(tag="nobr", attributes=kwargs)


def _Noembed(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Noembed)
def Noembed(**kwargs):
    return _HtmlImpl(tag="noembed", attributes=kwargs)


def _Noframes(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Noframes)
def Noframes(**kwargs):
    return _HtmlImpl(tag="noframes", attributes=kwargs)


def _Noscript(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Noscript)
def Noscript(**kwargs):
    return _HtmlImpl(tag="noscript", attributes=kwargs)


def _Object(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    border=None,
    data=None,
    form=None,
    height=None,
    name=None,
    type=None,
    usemap=None,
    width=None,
    children=[],
):
    ...


@implements(_Object)
def Object(**kwargs):
    return _HtmlImpl(tag="object", attributes=kwargs)


def _Ol(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    reversed=None,
    start=None,
    children=[],
):
    ...


@implements(_Ol)
def Ol(**kwargs):
    return _HtmlImpl(tag="ol", attributes=kwargs)


def _Optgroup(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    disabled=None,
    label=None,
    children=[],
):
    ...


@implements(_Optgroup)
def Optgroup(**kwargs):
    return _HtmlImpl(tag="optgroup", attributes=kwargs)


def _Option(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    disabled=None,
    label=None,
    selected=None,
    value=None,
    children=[],
):
    ...


@implements(_Option)
def Option(**kwargs):
    return _HtmlImpl(tag="option", attributes=kwargs)


def _Output(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    for_=None,
    form=None,
    name=None,
    children=[],
):
    ...


@implements(_Output)
def Output(**kwargs):
    return _HtmlImpl(tag="output", attributes=kwargs)


def _P(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_P)
def P(**kwargs):
    return _HtmlImpl(tag="p", attributes=kwargs)


def _Param(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    name=None,
    value=None,
    children=[],
):
    ...


@implements(_Param)
def Param(**kwargs):
    return _HtmlImpl(tag="param", attributes=kwargs)


def _Picture(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Picture)
def Picture(**kwargs):
    return _HtmlImpl(tag="picture", attributes=kwargs)


def _Plaintext(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Plaintext)
def Plaintext(**kwargs):
    return _HtmlImpl(tag="plaintext", attributes=kwargs)


def _Portal(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Portal)
def Portal(**kwargs):
    return _HtmlImpl(tag="portal", attributes=kwargs)


def _Pre(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Pre)
def Pre(**kwargs):
    return _HtmlImpl(tag="pre", attributes=kwargs)


def _Progress(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    form=None,
    max=None,
    value=None,
    children=[],
):
    ...


@implements(_Progress)
def Progress(**kwargs):
    return _HtmlImpl(tag="progress", attributes=kwargs)


def _Q(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    cite=None,
    children=[],
):
    ...


@implements(_Q)
def Q(**kwargs):
    return _HtmlImpl(tag="q", attributes=kwargs)


def _Rb(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Rb)
def Rb(**kwargs):
    return _HtmlImpl(tag="rb", attributes=kwargs)


def _Rp(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Rp)
def Rp(**kwargs):
    return _HtmlImpl(tag="rp", attributes=kwargs)


def _Rt(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Rt)
def Rt(**kwargs):
    return _HtmlImpl(tag="rt", attributes=kwargs)


def _Rtc(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Rtc)
def Rtc(**kwargs):
    return _HtmlImpl(tag="rtc", attributes=kwargs)


def _Ruby(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Ruby)
def Ruby(**kwargs):
    return _HtmlImpl(tag="ruby", attributes=kwargs)


def _S(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_S)
def S(**kwargs):
    return _HtmlImpl(tag="s", attributes=kwargs)


def _Samp(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Samp)
def Samp(**kwargs):
    return _HtmlImpl(tag="samp", attributes=kwargs)


def _Script(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    async_=None,
    charset=None,
    crossorigin=None,
    defer=None,
    importance=None,
    integrity=None,
    language=None,
    referrerpolicy=None,
    src=None,
    type=None,
    children=[],
):
    ...


@implements(_Script)
def Script(**kwargs):
    return _HtmlImpl(tag="script", attributes=kwargs)


def _Section(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Section)
def Section(**kwargs):
    return _HtmlImpl(tag="section", attributes=kwargs)


def _Select(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    autocomplete=None,
    autofocus=None,
    disabled=None,
    form=None,
    multiple=None,
    name=None,
    required=None,
    size=None,
    children=[],
):
    ...


@implements(_Select)
def Select(**kwargs):
    return _HtmlImpl(tag="select", attributes=kwargs)


def _Shadow(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Shadow)
def Shadow(**kwargs):
    return _HtmlImpl(tag="shadow", attributes=kwargs)


def _Slot(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Slot)
def Slot(**kwargs):
    return _HtmlImpl(tag="slot", attributes=kwargs)


def _Small(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Small)
def Small(**kwargs):
    return _HtmlImpl(tag="small", attributes=kwargs)


def _Source(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    media=None,
    sizes=None,
    src=None,
    srcset=None,
    type=None,
    children=[],
):
    ...


@implements(_Source)
def Source(**kwargs):
    return _HtmlImpl(tag="source", attributes=kwargs)


def _Spacer(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Spacer)
def Spacer(**kwargs):
    return _HtmlImpl(tag="spacer", attributes=kwargs)


def _Span(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Span)
def Span(**kwargs):
    return _HtmlImpl(tag="span", attributes=kwargs)


def _Strike(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Strike)
def Strike(**kwargs):
    return _HtmlImpl(tag="strike", attributes=kwargs)


def _Strong(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Strong)
def Strong(**kwargs):
    return _HtmlImpl(tag="strong", attributes=kwargs)


def _Style(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    media=None,
    scoped=None,
    type=None,
    children=[],
):
    ...


@implements(_Style)
def Style(**kwargs):
    return _HtmlImpl(tag="style", attributes=kwargs)


def _Sub(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Sub)
def Sub(**kwargs):
    return _HtmlImpl(tag="sub", attributes=kwargs)


def _Summary(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Summary)
def Summary(**kwargs):
    return _HtmlImpl(tag="summary", attributes=kwargs)


def _Sup(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Sup)
def Sup(**kwargs):
    return _HtmlImpl(tag="sup", attributes=kwargs)


def _Svg(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Svg)
def Svg(**kwargs):
    return _HtmlImpl(tag="svg", attributes=kwargs)


def _Table(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    background=None,
    bgcolor=None,
    border=None,
    summary=None,
    children=[],
):
    ...


@implements(_Table)
def Table(**kwargs):
    return _HtmlImpl(tag="table", attributes=kwargs)


def _Tbody(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    bgcolor=None,
    children=[],
):
    ...


@implements(_Tbody)
def Tbody(**kwargs):
    return _HtmlImpl(tag="tbody", attributes=kwargs)


def _Td(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    background=None,
    bgcolor=None,
    colspan=None,
    headers=None,
    rowspan=None,
    children=[],
):
    ...


@implements(_Td)
def Td(**kwargs):
    return _HtmlImpl(tag="td", attributes=kwargs)


def _Template(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Template)
def Template(**kwargs):
    return _HtmlImpl(tag="template", attributes=kwargs)


def _Textarea(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    autocomplete=None,
    autofocus=None,
    cols=None,
    dirname=None,
    disabled=None,
    enterkeyhint=None,
    form=None,
    inputmode=None,
    maxlength=None,
    minlength=None,
    name=None,
    placeholder=None,
    readonly=None,
    required=None,
    rows=None,
    wrap=None,
    children=[],
):
    ...


@implements(_Textarea)
def Textarea(**kwargs):
    return _HtmlImpl(tag="textarea", attributes=kwargs)


def _Tfoot(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    bgcolor=None,
    children=[],
):
    ...


@implements(_Tfoot)
def Tfoot(**kwargs):
    return _HtmlImpl(tag="tfoot", attributes=kwargs)


def _Th(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    background=None,
    bgcolor=None,
    colspan=None,
    headers=None,
    rowspan=None,
    scope=None,
    children=[],
):
    ...


@implements(_Th)
def Th(**kwargs):
    return _HtmlImpl(tag="th", attributes=kwargs)


def _Thead(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    children=[],
):
    ...


@implements(_Thead)
def Thead(**kwargs):
    return _HtmlImpl(tag="thead", attributes=kwargs)


def _Time(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    datetime=None,
    children=[],
):
    ...


@implements(_Time)
def Time(**kwargs):
    return _HtmlImpl(tag="time", attributes=kwargs)


def _Title(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Title)
def Title(**kwargs):
    return _HtmlImpl(tag="title", attributes=kwargs)


def _Tr(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    align=None,
    bgcolor=None,
    children=[],
):
    ...


@implements(_Tr)
def Tr(**kwargs):
    return _HtmlImpl(tag="tr", attributes=kwargs)


def _Track(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    default=None,
    kind=None,
    label=None,
    src=None,
    srclang=None,
    children=[],
):
    ...


@implements(_Track)
def Track(**kwargs):
    return _HtmlImpl(tag="track", attributes=kwargs)


def _Tt(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Tt)
def Tt(**kwargs):
    return _HtmlImpl(tag="tt", attributes=kwargs)


def _U(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_U)
def U(**kwargs):
    return _HtmlImpl(tag="u", attributes=kwargs)


def _Ul(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Ul)
def Ul(**kwargs):
    return _HtmlImpl(tag="ul", attributes=kwargs)


def _Var(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Var)
def Var(**kwargs):
    return _HtmlImpl(tag="var", attributes=kwargs)


def _Video(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    autoplay=None,
    buffered=None,
    controls=None,
    crossorigin=None,
    height=None,
    loop=None,
    muted=None,
    poster=None,
    preload=None,
    src=None,
    width=None,
    children=[],
):
    ...


@implements(_Video)
def Video(**kwargs):
    return _HtmlImpl(tag="video", attributes=kwargs)


def _Wbr(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Wbr)
def Wbr(**kwargs):
    return _HtmlImpl(tag="wbr", attributes=kwargs)


def _Xmp(
    accesskey=None,
    autocapitalize=None,
    class_=None,
    contenteditable=None,
    contextmenu=None,
    dir=None,
    draggable=None,
    hidden=None,
    id=None,
    itemprop=None,
    lang=None,
    role=None,
    slot=None,
    spellcheck=None,
    style=None,
    tabindex=None,
    title=None,
    translate=None,
    children=[],
):
    ...


@implements(_Xmp)
def Xmp(**kwargs):
    return _HtmlImpl(tag="xmp", attributes=kwargs)
