
# fully automated

    $ ./release.sh 0.1.0

# semi automated
To make a new release
```
# update react-ipywidgets/_version.py
$ git add -u && git commit -m 'Release v0.1.0' && git tag v0.1.0 && git push upstream master v0.1.0
```


If a problem happens, and you want to keep the history clean
```
# do fix
$ git rebase -i HEAD~3
$ git tag v0.1.0 -f &&  git push upstream master v0.1.0 -f
```
