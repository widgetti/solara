The solara server enables running ipywidgets based applications without a real Jupyter kernel, allowing multiple "Virtual kernels" to share the same process for better performance and scalability.

See https://solara.dev/documentation/advanced/understanding/solara-server for more details.

## Installation

```bash
pip install solara-server[starlette,dev]
```

## Usage

```bash
$ solara run myapp.py
```
