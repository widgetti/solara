import base64


def load_file_as_data_url(file_name, mime):
    with open(file_name, "rb") as f:
        data = f.read()
    return f"data:{mime};base64," + base64.b64encode(data).decode("utf-8")
