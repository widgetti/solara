# isort: skip_file
from .button import Button
from .style import Style
from .misc import (
    Navigator,
    GridDraggable,
    GridLayout,
    ListItem,
    ui_dropdown,
    ui_text,
    ui_checkbox,
    ui_slider,
    Text,
    Div,
    Preformatted,
    IconButton,
    HTML,
    VBox,
    HBox,
    Row,
    Column,
    GridFixed,
    Padding,
    FigurePlotly,
    Code,
)
from .alert import Warning, Info, Error, Success
from .checkbox import Checkbox
from .cross_filter import (
    CrossFilterDataFrame,
    CrossFilterReport,
    CrossFilterSelect,
    CrossFilterSlider,
)
from .datatable import DataTable, DataFrame
from .details import Details
from .file_browser import FileBrowser
from .image import Image
from .markdown import Markdown, MarkdownIt
from .slider import (
    DateSlider,
    FloatSlider,
    IntSlider,
    ValueSlider,
    SliderDate,
    SliderFloat,
    SliderInt,
    SliderValue,
    SliderRangeInt,
    SliderRangeFloat,
)
from .sql_code import SqlCode
from .togglebuttons import (
    ToggleButtonsMultiple,
    ToggleButtonsSingle,
)
from .input import InputText, InputFloat, InputInt
from .input_text_area import InputTextArea
from .pivot_table import PivotTableView, PivotTable, PivotTableCard
from .head import Head
from .title import Title
from .link import Link
from .applayout import AppLayout, Sidebar, AppBar, AppBarTitle
from .tab_navigation import TabNavigation
from .markdown_editor import MarkdownEditor
from .select import Select, SelectMultiple
from .matplotlib import FigureMatplotlib
from .echarts import FigureEcharts
from .figure_altair import FigureAltair, AltairChart
from .meta import Meta
from .columns import Columns, ColumnsResponsive
from .file_drop import FileDrop, FileDropMultiple
from .file_download import FileDownload
from .tooltip import Tooltip
from .card import Card, CardActions
from .spinner import SpinnerSolara
from .switch import Switch
from .progress import ProgressLinear
from .component_vue import _component_vue, component_vue
import reacton.core

try:
    from reacton import Fragment as Fragment  # type: ignore
except ImportError:
    pass

import logging
from ..settings import main


__all__ = [
    "Button",
    "Style",
    "Navigator",
    "GridDraggable",
    "GridLayout",
    "ListItem",
    "ui_dropdown",
    "ui_text",
    "ui_checkbox",
    "ui_slider",
    "Text",
    "Div",
    "Preformatted",
    "IconButton",
    "HTML",
    "VBox",
    "HBox",
    "Row",
    "Column",
    "GridFixed",
    "Padding",
    "FigurePlotly",
    "Code",
    "Warning",
    "Info",
    "Error",
    "Success",
    "Checkbox",
    "CrossFilterDataFrame",
    "CrossFilterReport",
    "CrossFilterSelect",
    "CrossFilterSlider",
    "DataTable",
    "DataFrame",
    "Details",
    "FileBrowser",
    "Image",
    "Markdown",
    "MarkdownIt",
    "DateSlider",
    "FloatSlider",
    "IntSlider",
    "ValueSlider",
    "SliderDate",
    "SliderFloat",
    "SliderInt",
    "SliderValue",
    "SliderRangeInt",
    "SliderRangeFloat",
    "SqlCode",
    "ToggleButtonsMultiple",
    "ToggleButtonsSingle",
    "InputText",
    "InputFloat",
    "InputInt",
    "InputTextArea",
    "PivotTableView",
    "PivotTable",
    "PivotTableCard",
    "Head",
    "Title",
    "Link",
    "AppLayout",
    "Sidebar",
    "AppBar",
    "AppBarTitle",
    "TabNavigation",
    "MarkdownEditor",
    "Select",
    "SelectMultiple",
    "FigureMatplotlib",
    "FigureEcharts",
    "FigureAltair",
    "AltairChart",
    "Meta",
    "Columns",
    "ColumnsResponsive",
    "FileDrop",
    "FileDropMultiple",
    "FileDownload",
    "Tooltip",
    "Card",
    "CardActions",
    "SpinnerSolara",
    "Switch",
    "ProgressLinear",
    "_component_vue",
    "component_vue",
]


_container = None

if main.default_container in globals():
    _container = globals()[main.default_container]
else:
    logger = logging.getLogger("solara.components")
    logger.warning(f"Default container {main.default_container} not found in solara.components. Defaulting to Column.")

reacton.core._default_container = _container or Fragment  # noqa: F405
