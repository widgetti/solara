from typing import Callable, Dict, List, Union, cast

import yaml
import markdown
import mkdocs_pycafe
import pymdownx.superfences

import solara
from solara.components.markdown import formatter, _no_deep_copy_emojione


# We want to separate metadata from the markdown files before rendering them, which solara.Markdown doesn't support
@solara.component
def MarkdownWithMetadata(content: str, unsafe_solara_execute=True):
    cleanups = solara.use_ref(cast(List[Callable[[], None]], []))
    if "---" in content:
        pre_content, raw_metadata, post_content = content.split("---")
        metadata: Dict[str, Union[str, List[str]]] = yaml.safe_load(raw_metadata)

        if len(pre_content) == 0:
            content = post_content
        else:
            content = pre_content + post_content

        if "title" not in metadata.keys():
            metadata["title"] = content.split("#")[1].split("\n")[0]

        for key, value in metadata.items():
            if key == "title":
                solara.Title(value)
            elif ":" in key:
                solara.Meta(property=key, content=value)
            else:
                solara.Meta(name=key, content=value)

    def make_markdown_object():
        return markdown.Markdown(  # type: ignore
            extensions=[
                "pymdownx.highlight",
                "pymdownx.superfences",
                "pymdownx.emoji",
                "toc",  # so we get anchors for h1 h2 etc
                "tables",
            ],
            extension_configs={
                "pymdownx.emoji": {
                    "emoji_index": _no_deep_copy_emojione,
                },
                "pymdownx.superfences": {
                    "custom_fences": [
                        {
                            "name": "mermaid",
                            "class": "mermaid",
                            "format": pymdownx.superfences.fence_div_format,
                        },
                        {
                            "name": "solara",
                            "class": "",
                            "validator": mkdocs_pycafe.validator,
                            "format": mkdocs_pycafe.formatter(
                                type="solara", next_formatter=formatter(unsafe_solara_execute, cleanups.current), inside_last_div=False
                            ),
                        },
                        {
                            "name": "python",
                            "class": "highlight",
                            "validator": mkdocs_pycafe.validator,
                            "format": mkdocs_pycafe.formatter(
                                type="solara", next_formatter=formatter(unsafe_solara_execute, cleanups.current), inside_last_div=False
                            ),
                        },
                    ],
                },
            },
        )

    md_parser = solara.use_memo(make_markdown_object, dependencies=[unsafe_solara_execute])

    def cleanup_wrapper():
        def cleanup():
            for cleanup in cleanups.current:
                cleanup()

        return cleanup

    solara.use_effect(cleanup_wrapper, [])

    with solara.v.Html(
        tag="div",
        style_="display: flex; flex-direction: row; justify-content: center; gap: 15px; max-width: 90%; margin: 0 auto;",
        attributes={"id": "markdown-to-navigate"},
    ):
        solara.Markdown(content, unsafe_solara_execute=unsafe_solara_execute, style="flex-grow: 1; max-width: min(100%, 1024px);", md_parser=md_parser)
        MarkdownNavigation(id="markdown-to-navigate").key("markdown-nav" + str(hash(content)))


@solara.component_vue("markdown_nav.vue")
def MarkdownNavigation(id: str):
    pass
