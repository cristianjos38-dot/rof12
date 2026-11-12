# Releasing ROF12

The package metadata is version `1.1.0`, matching `CHANGELOG.md` and the
`v1.1.0` GitHub release.

## Build and verify

```bash
python3.11 -m pip install build twine
python3.11 -m build
python3.11 -m twine check dist/*
```

## Publish to PyPI

Configure a PyPI API token through the local keyring or CI secret injection;
never place it in this repository or in chat. Then run:

```bash
python3.11 -m twine upload dist/*
```

This session built the sdist and wheel successfully but found no configured
PyPI token/keyring credentials, so publication was intentionally not attempted.
