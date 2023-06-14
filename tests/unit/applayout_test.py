import ipyvuetify as v

import solara


def test_sidebar():
    @solara.component
    def Content1():
        def on_click():
            print("click")  # noqa

        with solara.Card("Content") as content:
            with solara.Sidebar():
                solara.Button("Hi1", on_click=on_click)
            solara.Markdown("This is the content1")
        return content

    @solara.component
    def Content2():
        with solara.Card("Content") as content:
            solara.Title("Title2")
            with solara.Sidebar():
                solara.Button("Hi2")
            solara.Markdown("This is the content2")
        return content

    @solara.component
    def Sub3():
        with solara.Card("Sub3") as sub:
            solara.Markdown("Sub3 is the best")
            with solara.Sidebar():
                solara.Button("Hi3b")
        return sub

    @solara.component
    def Content3():
        with solara.Card("Content") as content:
            solara.Title("Title3")
            with solara.Sidebar():
                solara.Button("Hi3")
            solara.Markdown("This is the content3")
            Sub3()
        return content

    @solara.component
    def Content4():
        with solara.Card("Content") as content:
            solara.Title("Title4")
            solara.Markdown("This is the content4")
        return content

    @solara.component
    def Content5():
        with solara.Card("Content") as content:
            with solara.AppBarTitle():
                solara.Markdown("Title4")
                solara.Markdown("Title4b")
                solara.Markdown("Title4c")
            solara.Markdown("This is the content4")
        return content

    set_content = None

    @solara.component
    def Layout():
        nonlocal set_content
        content, set_content = solara.use_state(1)
        with solara.AppLayout(title="Scatter plot") as main:
            if content == 1:
                Content1()
            if content == 2:
                Content2()
            if content == 3:
                Content3()
            if content == 4:
                Content4()
            if content == 5:
                Content5()
        return main

    box, rc = solara.render(Layout(), handle_error=False)
    assert len(rc.find(v.NavigationDrawer).find(v.Btn, children=["Hi1"])) == 1
    rc.find(v.ToolbarTitle, children=["Scatter plot"]).assert_not_empty()
    assert set_content is not None
    set_content(2)
    assert len(rc.find(v.NavigationDrawer).find(v.Btn, children=["Hi1"])) == 0
    assert len(rc.find(v.NavigationDrawer).find(v.Btn, children=["Hi2"])) == 1
    assert len(rc.find(v.ToolbarTitle, children=["Title2"])) == 1
    set_content(1)
    assert len(rc.find(v.NavigationDrawer).find(v.Btn, children=["Hi1"])) == 1
    rc.find(v.ToolbarTitle, children=["Scatter plot"]).assert_not_empty()
    set_content(3)
    assert len(rc.find(v.NavigationDrawer).find(v.Btn)) == 2
    assert len(rc.find(v.ToolbarTitle, children=["Title3"])) == 1
    set_content(4)
    rc.find(v.NavigationDrawer).assert_empty()
    set_content(5)
    assert len(rc.find(v.ToolbarTitle).widget.children) == 3
