import pathlib
import shutil
import subprocess
import tempfile

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

packages = [
    ["@widgetti/solara-vuetify-app", "2.1.0"],
    ["requirejs", "2.3.6"],
    ["mermaid", "8.6.4"],
    ["codemirror", "5.65.3"],
    ["vega", "5.21.0"],
    ["vega-lite", "5.2.0"],
    ["vega-embed", "6.20.2"],
    ["@widgetti/vue-grid-layout", "2.3.13-alpha.2"],
    ["@widgetti/solara-milkdown", "6.3.0"],
]


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
