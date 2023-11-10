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


def test_no_rerender():
    have_sidebar = solara.reactive(False)
    have_app_bar = solara.reactive(False)
    content_use_effects = 0
    content_renders = 0
    app_bar_use_effects = 0
    app_bar_renders = 0

    @solara.component
    def AppBarComponent():
        nonlocal app_bar_renders, app_bar_use_effects

        def effect():
            nonlocal app_bar_use_effects
            app_bar_use_effects += 1

        solara.use_effect(effect, [])
        app_bar_renders += 1
        solara.Button("1")
        solara.Button("2")

    @solara.component
    def Content():
        nonlocal content_renders, content_use_effects

        def effect():
            nonlocal content_use_effects
            content_use_effects += 1

        solara.use_effect(effect, [])
        content_renders += 1
        if have_app_bar.value:
            with solara.AppBar():
                AppBarComponent()

        if have_sidebar.value:
            with solara.Sidebar():
                solara.Button("Hi")
        with solara.Card("Content"):
            solara.Markdown("This is the content")

    @solara.component
    def Layout():
        with solara.AppLayout(title="Test"):
            Content()

    box, rc = solara.render(Layout(), handle_error=False)
    assert len(rc.find(v.NavigationDrawer).find(v.Btn, children=["Hi"])) == 0
    assert len(rc.find(v.AppBar).find(v.Btn)) == 0
    assert content_renders == 1
    assert content_use_effects == 1
    assert app_bar_renders == 0
    assert app_bar_use_effects == 0

    have_app_bar.value = True
    assert len(rc.find(v.AppBar).find(v.Btn)) == 2
    assert content_renders == 2
    assert content_use_effects == 1
    assert app_bar_renders == 1
    assert app_bar_use_effects == 1

    have_sidebar.value = True
    assert len(rc.find(v.NavigationDrawer).find(v.Btn, children=["Hi"])) == 1
    assert len(rc.find(v.AppBar).find(v.Btn)) == 2
    assert content_renders == 3
    assert content_use_effects == 1
    assert app_bar_renders == 1
    assert app_bar_use_effects == 1
    rc.close()

    # now, a render with in 1 go
    content_renders = 0
    content_use_effects = 0
    app_bar_renders = 0
    app_bar_use_effects = 0
    box, rc = solara.render(Layout(), handle_error=False)
    assert len(rc.find(v.NavigationDrawer).find(v.Btn, children=["Hi"])) == 1
    assert len(rc.find(v.AppBar).find(v.Btn)) == 2
    assert content_renders == 1
    assert content_use_effects == 1
    assert app_bar_renders == 1
    assert app_bar_use_effects == 1
