"""Relative imports in component scripts: each imported file becomes its own ES module.

Only static imports are rewritten. A dynamic `import("./x.js")` is left as is, and does not work.
Comments and string literals are skipped, so an import inside them is not rewritten.
Regular expression literals are not understood: a quote or `//` inside one can hide the code after it.
An import-like string inside a nested template literal (`${`import "./x.js"`}` inside backticks) is still
rewritten, because a regular expression cannot track that nesting.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Callable

import ipyreact
from solara.server.reload import watch_file

_RELATIVE_IMPORT = re.compile(
    r"""
    # Comments and string literals, kept as they are. They are matched where they start, so an import inside is skipped.
    (?P<skip>
        //[^\n]*
      | /\*.*?\*/
      | "(?:\\.|[^"\\\n])*"
      | '(?:\\.|[^'\\\n])*'
      | `(?:\\.|[^`\\])*`
    )
    # `import x from "./a.js"`, `import "./a.js"` and `export ... from "./a.js"`, with single or double quotes.
    # Between `import` or `export` and `from` there can be comments, but no string, call or other `/`.
  | (?P<head>
        \b(?:import|export)\b(?:[^'"`();/] | /\*(?:[^*]|\*(?!/))*\*/ | //[^\n]*\n)*?\bfrom\s*
      | \bimport\s*
    )
    (?P<quote>["'])(?P<specifier>\.\.?/[^'"\n]*)(?P=quote)
    """,
    re.DOTALL | re.VERBOSE,
)


def module_name(code: str) -> str:
    """The ES module name for some code, by content.

    The browser cannot point an existing module name at new code, so an edit must give a new name
    for hot reload to show it. Imported names are part of the importer's code, so the change propagates.
    """
    return "solara-html-" + hashlib.sha256(code.encode()).hexdigest()[:12]


def rewrite_relative_imports(code: str, to_name: Callable[[str], str]) -> str:
    """Replace each relative import specifier in `code` with `to_name(specifier)`."""

    def replace(match: re.Match[str]) -> str:
        if match.group("skip") is not None:
            return match.group("skip")
        quote = match.group("quote")
        return match.group("head") + quote + to_name(match.group("specifier")) + quote

    return _RELATIVE_IMPORT.sub(replace, code)


def define_imports(code: str, importer: Path) -> str:
    """Define the files that `code` imports relatively, depth-first, and return the rewritten code.

    Each file is defined once, before the modules that import it, and is watched for hot reload.
    """
    return _define_imports(code, importer.resolve(), {}, (importer.resolve(),))


def _define_imports(code: str, importer: Path, defined: dict[Path, str], stack: tuple[Path, ...]) -> str:
    def to_name(specifier: str) -> str:
        path = (importer.parent / specifier).resolve()
        if path in stack:
            raise ValueError("import cycle: " + " -> ".join(str(p) for p in stack[stack.index(path) :] + (path,)))
        if path not in defined:
            if not path.is_file():
                raise ValueError(f"{importer}: imported file {specifier!r} does not exist ({path})")
            watch_file(path)
            rewritten = _define_imports(path.read_text(encoding="utf-8"), path, defined, stack + (path,))
            defined[path] = module_name(rewritten)
            ipyreact.define_module(defined[path], code=rewritten)
        return defined[path]

    return rewrite_relative_imports(code, to_name)
