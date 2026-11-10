---
title: Linking to the Solara API docs from Sphinx (intersphinx)
description: Use intersphinx to link from your own Sphinx documentation to the Solara API reference.
---
# Intersphinx

If your project uses [Sphinx](https://www.sphinx-doc.org/), you can link to the Solara API documentation with the
[intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html) extension.

Solara publishes an inventory file at:

```
https://solara.dev/static/public/objects.inv
```

The inventory is not at the default location (`https://solara.dev/objects.inv`), so give its URL as the second item of the tuple.

## Configuration

Add this to the `conf.py` of your Sphinx project:

```python
extensions = [
    "sphinx.ext.intersphinx",
]

intersphinx_mapping = {
    "solara": ("https://solara.dev/", "https://solara.dev/static/public/objects.inv"),
}
```

## Examples

In reStructuredText:

```rst
Use :func:`solara.Button` to make a button, and :func:`solara.use_reactive` to keep state.

The :class:`solara.Route` class defines a page in a multipage app.

Pages that document more objects link to the correct heading, for example :func:`solara.SliderInt`.

Use your own link text: :func:`a text area <solara.InputTextArea>`.

Use the ``solara:`` prefix if another inventory has the same name: :func:`solara:solara.Markdown`.
```

In Markdown with [MyST](https://myst-parser.readthedocs.io/):

```markdown
Use {py:func}`solara.Button` to make a button.

Lab features work too: {py:func}`solara.lab.computed` and {py:func}`solara.lab.ConfirmationDialog`.
```

In a docstring rendered by `sphinx.ext.autodoc`:

```python
def MyComponent(value: solara.Reactive[int]):
    """Show a slider for the value.

    This wraps :func:`solara.SliderInt`, see also :func:`solara.use_reactive`.
    """
```

## Which names are available

Each documented object is in the inventory under its public name and under its full module path. For example, these
names all link to the same page:

 * `solara.SliderInt`
 * `solara.components.slider.SliderInt`

Components (for example `solara.Button`) and functions use the `py:function` role, so use `:func:` for them.
Classes (for example `solara.Route`) use the `py:class` role, so use `:class:` for them.
Objects such as `solara.lab.cookies` use the `py:data` role, so use `:data:` for them.
`:py:obj:` matches either one.

Solara also re-exports names from [Reacton](https://reacton.solara.dev/), such as `solara.use_ref`. The Solara inventory does not list these names.
Add the [Reacton](https://reacton.solara.dev/) inventory and link to `reacton.use_ref` instead:

```python
intersphinx_mapping = {
    "solara": ("https://solara.dev/", "https://solara.dev/static/public/objects.inv"),
    "reacton": ("https://reacton.solara.dev/en/latest/", None),
}
```

To see all names in the inventory, run:

```bash
python -m sphinx.ext.intersphinx https://solara.dev/static/public/objects.inv
```

## For Solara contributors

The website builds the inventory from the `apidoc(...)` calls in the API pages
(see `solara/website/intersphinx.py`). After you add, rename, or move an API page, run this command and commit the
changed `solara/website/public/objects.inv`:

```bash
python -m solara.website.intersphinx
```

A unit test fails when the committed file is out of date.
