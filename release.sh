#/bin/bash
set -e -o pipefail
# usage: ./release minor -n
version=$(bump2version --dry-run --list $* | grep new_version | sed -r s,"^.*=",,)
echo Version tag v$version
bumpversion $* --verbose && git push upstream master v$version
