import solara


def callback(event):
    print("Event received:", event)


@solara.component_vue("test_pywebview.vue")
def TestPywebview(event_callback):
    pass


@solara.component
def Page():
    TestPywebview(event_callback=callback)
    # html = "<script>pywebview.api.test(\"Test passes!\")</script>Script tag inserted"
    # solara.HTML(unsafe_innerHTML=html)
