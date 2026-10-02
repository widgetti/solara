import json
import unittest.mock
from pathlib import Path

import pytest

import solara_html.imports
from solara_html.imports import define_imports, module_name, rewrite_relative_imports


def test_rewrite_static_relative_imports_only():
    code = """
import a from "./a.js";
import { b,
  c } from '../b.js';
import "./side.js";
export * from "./d.js";
export { e } from './e.js';
import React from "react";
const lazy = import("./lazy.js");
"""
    rewritten = rewrite_relative_imports(code, lambda specifier: "m:" + specifier)

    assert 'import a from "m:./a.js";' in rewritten
    assert "c } from 'm:../b.js';" in rewritten
    assert 'import "m:./side.js";' in rewritten
    assert 'export * from "m:./d.js";' in rewritten
    assert "export { e } from 'm:./e.js';" in rewritten
    assert 'import React from "react";' in rewritten
    assert 'import("./lazy.js")' in rewritten


def test_rewrite_skips_comments_and_strings():
    code = r"""
// import "./line.js";
/* import a from "./block.js";
   export * from "./block2.js"; */
const s = 'import "./single.js"';
const d = "import \"./double.js\"; import './inner.js'";
const t = `import x from "./template.js"`;
export { a } // from "./trailing.js"
import b from "./real.js";
"""
    rewritten = rewrite_relative_imports(code, lambda specifier: "m:" + specifier)

    assert rewritten == code.replace('"./real.js"', '"m:./real.js"')


def test_rewrite_import_with_comments_before_from():
    code = """
import x /* c */ from "./x.js";
import { a, // note
  b } from './y.js';
"""
    rewritten = rewrite_relative_imports(code, lambda specifier: "m:" + specifier)

    assert rewritten == code.replace('"./x.js"', '"m:./x.js"').replace("'./y.js'", "'m:./y.js'")


def test_rewrite_leaves_json_template_string_alone():
    # The generated component code holds the template as a JSON string.
    code = 'import "./a.js";\nconst template = ' + json.dumps("<script type=\"module\">import './b.js';</script>") + ";"

    rewritten = rewrite_relative_imports(code, lambda specifier: "m:" + specifier)

    assert rewritten == code.replace('"./a.js"', '"m:./a.js"')


def test_define_imports_ignores_commented_import_of_missing_file(tmp_path: Path, define_module):
    code = '// import "./missing.js";\nexport const a = 1;'

    assert define_imports(code, tmp_path / "main.html") == code
    define_module.assert_not_called()


@pytest.fixture
def define_module():
    with unittest.mock.patch.object(solara_html.imports.ipyreact, "define_module") as define_module, unittest.mock.patch.object(
        solara_html.imports, "watch_file"
    ):
        yield define_module


def test_define_imports_depth_first_and_once(tmp_path: Path, define_module):
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "a.js").write_text('import { c } from "./c.js";\nexport const a = c;', encoding="utf-8")
    (tmp_path / "lib" / "c.js").write_text("export const c = 1;", encoding="utf-8")
    (tmp_path / "b.js").write_text('import { c } from "./lib/c.js";\nexport const b = c;', encoding="utf-8")

    code = define_imports('import { a } from "./lib/a.js";\nimport { b } from "./b.js";', tmp_path / "main.html")

    c, a, b = (call.args[0] for call in define_module.call_args_list)
    assert c == module_name("export const c = 1;")
    assert define_module.call_args_list[1].kwargs["code"] == f'import {{ c }} from "{c}";\nexport const a = c;'
    assert code == f'import {{ a }} from "{a}";\nimport {{ b }} from "{b}";'


def test_define_imports_missing_file_names_importer(tmp_path: Path, define_module):
    (tmp_path / "a.js").write_text('import "./missing.js";', encoding="utf-8")

    with pytest.raises(ValueError, match=r"a\.js: imported file './missing.js' does not exist"):
        define_imports('import "./a.js";', tmp_path / "main.html")


def test_define_imports_cycle(tmp_path: Path, define_module):
    (tmp_path / "a.js").write_text('import "./b.js";', encoding="utf-8")
    (tmp_path / "b.js").write_text('import "./a.js";', encoding="utf-8")

    with pytest.raises(ValueError, match="import cycle"):
        define_imports('import "./a.js";', tmp_path / "main.html")


def test_module_name_is_by_content():
    assert module_name("export const a = 1;") == module_name("export const a = 1;")
    assert module_name("export const a = 1;") != module_name("export const a = 2;")
