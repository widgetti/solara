# # tests all pages in the api docs
# from pathlib import Path

# import playwright.sync_api

# import solara

# HERE = Path(__file__).parent


# md = """

# # Solara markdown

# ```solara
# import solara


# @solara.component
# def ClickButton():
#     clicks, set_clicks = solara.use_state(0)
#     def on_click():
#         set_clicks(clicks + 1)
#         print("clicks", clicks)

#     return solara.Button(label=f"Clicked: {clicks}", on_click=on_click)


# app = ClickButton()
# ```

# """


# @solara.component
# def MarkdownApp():
#     return solara.Markdown(md, unsafe_solara_execute=True)


# @solara.component
# def MarkdownAppOff():
#     return solara.Markdown(md, unsafe_solara_execute=False)


# @solara.component
# def MarkdownItApp():
#     return solara.MarkdownIt(md, unsafe_solara_execute=True)


# @solara.component
# def MarkdownItAppOff():
#     return solara.MarkdownIt(md, unsafe_solara_execute=False)


# def test_markdown(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
#     with extra_include_path(HERE), solara_app("markdown_test:MarkdownApp"):
#         page_session.goto(solara_server.base_url)
#         page_session.locator("text=Clicked: 0").wait_for()
#         # TODO: flakey test
#         page_session.locator("text=Clicked: 0").click()
#         # page_session.locator("text=Clicked: 1").wait_for()


# def test_markdown_no_execute(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
#     with extra_include_path(HERE), solara_app("markdown_test:MarkdownAppOff"):
#         page_session.goto(solara_server.base_url)
#         page_session.locator("text=Solara execution is not enabled").wait_for()


# def test_markdown_it(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
#     with extra_include_path(HERE), solara_app("markdown_test:MarkdownItApp"):
#         page_session.goto(solara_server.base_url)
#         page_session.locator("text=Clicked: 0").wait_for()
#         page_session.locator("text=Clicked: 0").click()
#         # TODO: flakey test
#         # page_session.locator("text=Clicked: 1").wait_for()


# def test_markdown_it_no_execute(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
#     with extra_include_path(HERE), solara_app("markdown_test:MarkdownItAppOff"):
#         page_session.goto(solara_server.base_url)
#         page_session.locator("text=Solara execution is not enabled").wait_for()
