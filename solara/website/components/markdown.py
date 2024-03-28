from typing import Dict, List, Union

import yaml

import solara


# We want to separate metadata from the markdown files before rendering them, which solara.Markdown doesn't support
@solara.component
def MarkdownWithMetadata(content: str, unsafe_solara_execute=True):
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
    solara.Markdown(content, unsafe_solara_execute=unsafe_solara_execute)
