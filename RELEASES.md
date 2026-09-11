# Release process

Only tags are used by now (not releases).

# Tagging a release

If a version needs to be changed, edit `tk_date_entry/__version__.py`.

This file is read by *pyproject.toml* (dynamic version attribute).

If the version is not changed, the publishing procedure works using the same version with a different build number.

Push all changes:

```shell
git commit -a
git push
```

_After pushing the last commit_, add a local tag (shall be added AFTER the commit that needs to be published):

```shell
git tag # list local tags
git tag v1.0.0
```

Notes:

- correspondence between tag and `__version__.py` is not automatic.
- the tag must start with "v" if a GitHub Action workflow needs to be run

Push this tag to the origin, which starts the PyPI publishing workflow (GitHub Action):

```shell
git push origin v1.0.0
git ls-remote --tags https://github.com/Ircama/tk_date_entry # list remote tags
```

Check the published tag here: https://github.com/Ircama/tk_date_entry/tags

It shall be even with the last commit.

Check the GitHub Action: https://github.com/Ircama/tk_date_entry/actions

Check PyPI:

- https://test.pypi.org/manage/project/tk-date-entry/releases/
- https://pypi.org/manage/project/tk-date-entry/releases/

End user publishing page:

- https://test.pypi.org/project/tk-date-entry
- https://pypi.org/project/tk-date-entry/

Verify whether wrong builds need to be removed.

Test installation:

```shell
cd
python3 -m pip uninstall -y tk-date-entry
python3 -m pip install tk-date-entry
python3 -c "from tk_date_entry import DateEntry; print(DateEntry)"
python3 -m pip uninstall -y tk-date-entry
```

# Updating the same tag (using a different build number for publishing)

```shell
git tag # list tags
git tag -d v1.0.0 # remove local tag
git push --delete origin v1.0.0 # remove remote tag
git ls-remote --tags https://github.com/Ircama/tk_date_entry # list remote tags
```

Then follow the tagging procedure again to add the tag to the latest commit.

# Testing the build procedure locally

```shell
cd <repository directory>
```

## Local build (using build):

```shell
python3 -m build --sdist --wheel --outdir dist/ .
python3 -m twine upload --repository testpypi dist/*
```

## Removing directories

```shell
ls -l dist
rm -r build dist tk_date_entry.egg-info
```
