import solara


@solara.component_vue("test_pywebview.vue")
def TestPywebview():
    pass


@solara.component
def Page():
    TestPywebview()
    # html = "<script>pywebview.api.test(\"Test passes!\")</script>Script tag inserted"
    # solara.HTML(unsafe_innerHTML=html)
