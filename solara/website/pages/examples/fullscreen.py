import solara


@solara.component
def Page():
    with solara.Card("Fullscreen apps"):
        solara.Markdown(
            """
        These examples need to be run in the full browser window

         * [Streamlit users tutorial](/apps/tutorial-streamlit)
         * [Scatter plot app](/apps/scatter)
         * [Multipage](/apps/multipage)
         * [Layout demo](/apps/layout-demo)

        """
        )
