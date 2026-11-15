# Deployment Guide

Package: `nima-persianguard` 1.1.0. License metadata uses PEP 639 (`license = "MIT"`) and includes `LICENSE` via `license-files = ["LICENSE"]`.

## Build and verify

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

The build produces a wheel and a source distribution in `dist/`. Review the installed package and metadata before publishing.

## Publish

Use a PyPI API token and keep it private. Test on TestPyPI first, then publish the verified artifacts to PyPI with Twine.

Before updating Zenodo, compare the release version, DOI record, included `LICENSE`, and MIT license metadata against these artifacts.

© copyright 2026 nima esmaeili
