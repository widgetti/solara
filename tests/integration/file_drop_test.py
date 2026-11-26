import playwright.sync_api
import pytest

import solara


@pytest.mark.parametrize(
    ("accept", "multiple", "files", "expected"),
    [
        (".csv", False, [("data.csv", "text/plain"), ("data.txt", "text/csv")], "data.csv"),
        ("text/csv", False, [("data.txt", "text/csv"), ("data.csv", "text/plain")], "data.txt"),
        ("image/*", False, [("photo.png", "image/png"), ("data.csv", "text/csv")], "photo.png"),
        (None, False, [("data.bin", "application/octet-stream")], "data.bin"),
        (".csv, image/*", True, [("data.csv", "text/plain"), ("notes.txt", "text/plain"), ("photo.png", "image/png")], "data.csv,photo.png"),
    ],
)
def test_file_drop_accept(
    solara_test,
    page_session: playwright.sync_api.Page,
    accept,
    multiple: bool,
    files,
    expected: str,
):
    @solara.component
    def Page():
        received = solara.use_reactive("none")

        if multiple:
            solara.FileDropMultiple(accept=accept, on_file=lambda value: received.set(",".join(file["name"] for file in value)))
        else:
            solara.FileDrop(accept=accept, on_file=lambda value: received.set(value["name"]))
        solara.Text(received.value, classes=["received-files"])

    solara.display(Page())
    page_session.locator(".solara-file-drop").evaluate(
        """(element, files) => {
            const event = new Event('drop', {bubbles: true});
            Object.defineProperty(event, 'dataTransfer', {
                value: {
                    items: files.map(([name, type]) => ({
                        webkitGetAsEntry: () => ({
                            isFile: true,
                            file: resolve => resolve(new File(['content'], name, {type})),
                        }),
                    })),
                },
            });
            element.dispatchEvent(event);
        }""",
        files,
    )
    playwright.sync_api.expect(page_session.locator(".received-files")).to_have_text(expected)
