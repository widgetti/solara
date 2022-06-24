
# fully automated

    $ ./release.sh 0.4.3a2

# semi automated
To make a new release
```
# update react-ipywidgets/_version.py
$ git add -u && git commit -m 'Release v0.4.3a2' && git tag v0.4.3a2 && git push upstream master v0.4.3a2
```


If a problem happens, and you want to keep the history clean
```
# do fix
$ git rebase -i HEAD~3
$ git tag v0.4.3a2 -f &&  git push upstream master v0.4.3a2 -f
```
