import solara


@solara.component
def Page():
    volume, set_volume = solara.use_state(5)
    with solara.VBox() as main:
        solara.Markdown("# Choose your volume")
        solara.IntSlider("Volume", value=volume, on_value=set_volume, min=0, max=11)
        if volume == 11:
            solara.Markdown(f"Yeah! {volume} is the best volume!")
    return main
