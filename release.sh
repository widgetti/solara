#!/bin/bash
set -e -o pipefail
# usage: ./release minor -n
# (git diff --quiet master @widgetti/solara-vuetify-app@10.0.3 -- packages/solara-vuetify-app) || {\
#     echo -e "\033[31m There are unreleased changes to the solara-vuetify-app package.\n Please release the javascript package before Solara by running \n\n \
#     \033[0m (cd packages/solara-vuetify-app && ./release.sh <patch | minor | major> -n)\n"; \
#     exit 1;}
(git diff --quiet master @widgetti/solara-vuetify3-app@5.0.2 -- packages/solara-vuetify3-app) || {\
    echo -e "\033[31m There are unreleased changes to the solara-vuetify3-app package.\n Please release the javascript package before Solara by running \n\n \
    \033[0m (cd packages/solara-vuetify3-app && ./release.sh <patch | minor | major> -n)\n"; \
    exit 1;}
(git diff --quiet master @widgetti/solara-vuetify3-app@5.0.2 -- packages/solara-widget-manager) || {\
    echo -e "\033[31m There are unreleased changes to the solara-widget-manager package.\n Please release the javascript package before Solara by running \n\n \
    \033[0m (cd packages/solara-vuetify-app && ./release.sh <patch | minor | major> -n) && \
    (cd packages/solara-vuetify3-app && ./release.sh <patch | minor | major> -n)\n"; \
    exit 1;}
(git diff --quiet master @widgetti/solara-vuetify3-app@5.0.2 -- packages/solara-widget-manager8) || {\
    echo -e "\033[31m There are unreleased changes to the solara-widget-manager8 package.\n Please release the javascript package before Solara by running \n\n \
    \033[0m (cd packages/solara-vuetify-app && ./release.sh <patch | minor | major> -n) && \
    (cd packages/solara-vuetify3-app && ./release.sh <patch | minor | major> -n)\n"; \
    exit 1;}

version=$(bump2version --dry-run --list $* | grep new_version | sed -r s,"^.*=",,)
echo Version tag v$version
bumpversion $* --verbose && git push upstream master v$version
