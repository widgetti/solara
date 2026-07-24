import pathlib
import shutil
import subprocess
import tempfile

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

packages = [
    ["@widgetti/solara-vuetify-app", "10.1.1"],
    ["@widgetti/solara-vuetify3-app", "5.1.1"],
    ["requirejs", "2.3.6"],
    ["mermaid", "10.8.0"],
    ["codemirror", "5.65.3"],
    ["vega", "5.21.0"],
    ["vega-lite", "5.2.0"],
    ["vega-embed", "6.20.2"],
    ["@widgetti/vue-grid-layout", "2.3.13-alpha.2"],
    ["@widgetti/solara-milkdown", "6.3.0"],
    ["echarts", "5.4.0"],
    ["font-awesome", "4.5.0"],
]


# Per-package prune rules applied after npm pack, to keep the solara-assets
# wheel under PyPI's 10 GB per-project storage cap.
# Each entry is a list of glob patterns (relative to the package root) whose
# matching files/directories are removed. Kept intentionally conservative:
# only paths never referenced from solara's template/components.
PRUNE_PATTERNS_ALL = [
    # Source maps: only used by browsers with devtools open on the CDN host.
    # Missing .map ⇒ devtools shows a benign "sourcemap not available".
    "**/*.map",
]
PRUNE_PATTERNS_PER_PACKAGE = {
    # echarts: solara only loads dist/echarts.js. The rest is dev/build stuff.
    "echarts": ["lib", "types", "extension-src", "build"],
    # mermaid: solara only loads dist/mermaid.min.js. mermaid.js is the 6+ MB
    # unminified twin — nothing in the template/components points at it.
    "mermaid": ["dist/mermaid.js"],
}


def prune_package(package_dir: pathlib.Path, package: str):
    package_key = package.split("/")[-1]  # "@widgetti/foo" -> "foo"
    patterns = list(PRUNE_PATTERNS_ALL) + PRUNE_PATTERNS_PER_PACKAGE.get(package_key, [])
    removed_bytes = 0
    for pattern in patterns:
        for match in package_dir.glob(pattern):
            if match.is_dir():
                removed_bytes += sum(p.stat().st_size for p in match.rglob("*") if p.is_file())
                shutil.rmtree(match)
            elif match.is_file():
                removed_bytes += match.stat().st_size
                match.unlink()
    if removed_bytes:
        print(f"package: {package} pruned {removed_bytes // 1024} KB of dev artifacts")  # noqa


def npm_pack(base_cache_dir: pathlib.Path, package: str, version: str):
    with tempfile.TemporaryDirectory() as temp_dir_name:
        target_directory = base_cache_dir / f"{package}@{version}"
        if target_directory.exists():
            if (target_directory / "package.json").exists():
                print(f"package: {package} already downloaded, skipping")  # noqa
                return
            else:
                # if the directory exists and we 'move', the directory will be
                # moved to the 'package' subdirectory, so remove it first
                target_directory.unlink()
        try:
            subprocess.check_call(f"npm pack {package}@{version}", cwd=temp_dir_name, shell=True)
            package_file_name = package
            if package.startswith("@"):
                package_file_name = package[1:].replace("/", "-")
            subprocess.check_call(f"tar xzf {package_file_name}-{version}.tgz", cwd=temp_dir_name, shell=True)
            shutil.move(str(pathlib.Path(temp_dir_name) / "package"), str(target_directory))
            prune_package(target_directory, package)
        except Exception:
            # creating for convenience, to unpack a tarball
            # in the right directory
            target_directory.mkdir(exist_ok=True, parents=True)
            raise


def download_cdn(cache_dir):
    for package, version in packages:
        npm_pack(cache_dir, package, version)


class CustomHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if self.target_name not in ["wheel", "sdist"]:
            return
        download_cdn(pathlib.Path("cdn"))
