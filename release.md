
# Fully automated

    $ ./release.sh patch


## Making an alpha release


    $ ./release.sh patch --new-version 1.17.4a1


# semi automated
To make a new release
```
# update solara/__init__.py
$ git add -u && git commit -m 'Release v1.17.4' && git tag v1.17.4 && git push upstream master v1.17.4
```


If a problem happens, and you want to keep the history clean
```
# do fix
$ git rebase -i HEAD~3
$ git tag v1.17.4 -f &&  git push upstream master v1.17.4 -f
```
