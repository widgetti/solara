#!/bin/bash
set -e -o pipefail
# usage: ./release minor -n
# the page links the chunk files of both apps (solara/server/frontend_assets.py), so both need a release
(git diff --quiet master @widgetti/solara-vuetify-app@10.1.1 -- packages/solara-vuetify-app packages/solara-widget-manager packages/solara-widget-manager8) || {\
    echo -e "\033[31m There are unreleased changes to the solara-vuetify-app package (or the widget manager it bundles).\n Please release the javascript package before Solara by running \n\n \
    \033[0m (cd packages/solara-vuetify-app && ./release.sh <patch | minor | major> -n)\n"; \
    exit 1;}
(git diff --quiet master @widgetti/solara-vuetify3-app@5.2.0 -- packages/solara-vuetify3-app) || {\
    echo -e "\033[31m There are unreleased changes to the solara-vuetify3-app package.\n Please release the javascript package before Solara by running \n\n \
    \033[0m (cd packages/solara-vuetify3-app && ./release.sh <patch | minor | major> -n)\n"; \
    exit 1;}
(git diff --quiet master @widgetti/solara-vuetify3-app@5.2.0 -- packages/solara-widget-manager) || {\
    echo -e "\033[31m There are unreleased changes to the solara-widget-manager package.\n Please release the javascript package before Solara by running \n\n \
    \033[0m (cd packages/solara-vuetify-app && ./release.sh <patch | minor | major> -n) && \
    (cd packages/solara-vuetify3-app && ./release.sh <patch | minor | major> -n)\n"; \
    exit 1;}
(git diff --quiet master @widgetti/solara-vuetify3-app@5.2.0 -- packages/solara-widget-manager8) || {\
    echo -e "\033[31m There are unreleased changes to the solara-widget-manager8 package.\n Please release the javascript package before Solara by running \n\n \
    \033[0m (cd packages/solara-vuetify-app && ./release.sh <patch | minor | major> -n) && \
    (cd packages/solara-vuetify3-app && ./release.sh <patch | minor | major> -n)\n"; \
    exit 1;}

version=$(bump2version --dry-run --list $* | grep new_version | sed -r s,"^.*=",,)
echo Version tag v$version
bumpversion $* --verbose && git push upstream master v$version
