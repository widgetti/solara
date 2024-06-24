from typing import cast
import ipyvue
import solara
import traitlets


class PDFViewerWidget(ipyvue.VueTemplate):
    template_file = (__file__, "pdf_viewer.vue")

    pdf_name_b64_map = traitlets.Dict({}).tag(sync=True)
    current_file = traitlets.Unicode("").tag(sync=True)
    height = traitlets.Unicode("500px").tag(sync=True)

    def __repr__(self):
        return f"PDFViewerWidget(files={list(self.pdf_name_b64_map)}, active_file={self.current_file})"


@solara.component
def PDFViewer(
    pdf_name_b64_map: dict[str, str], current_file: solara.Reactive[str], **kwargs
):
    if pdf_name_b64_map is None:
        pdf_name_b64_map = {}

    def on_load():
        real = cast(PDFViewerWidget, solara.get_widget(widget))
        real.current_file = current_file.value

    solara.use_effect(on_load, [current_file.value])
    widget = PDFViewerWidget.element(pdf_name_b64_map=pdf_name_b64_map, **kwargs)  # type: ignore
