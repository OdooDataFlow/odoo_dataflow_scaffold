# Odoo_Dataflow_Scaffold

[![PyPI](https://img.shields.io/pypi/v/odoo_dataflow_scaffold.svg)][pypi status]
[![Status](https://img.shields.io/pypi/status/odoo_dataflow_scaffold.svg)][pypi status]
[![Python Version](https://img.shields.io/pypi/pyversions/odoo_dataflow_scaffold)][pypi status]
[![License](https://img.shields.io/pypi/l/odoo_dataflow_scaffold)][license]

[![Read the documentation at https://odoo_dataflow_scaffold.readthedocs.io/](https://img.shields.io/readthedocs/odoo_dataflow_scaffold/latest.svg?label=Read%20the%20Docs)][read the docs]
[![Tests](https://github.com/bosd/odoo_dataflow_scaffold/workflows/Tests/badge.svg)][tests]
[![Codecov](https://codecov.io/gh/bosd/odoo_dataflow_scaffold/branch/main/graph/badge.svg)][codecov]

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)][pre-commit]
[![Ruff codestyle][ruff badge]][ruff project]

[pypi status]: https://pypi.org/project/odoo_dataflow_scaffold/
[read the docs]: https://odoo_dataflow_scaffold.readthedocs.io/
[tests]: https://github.com/bosd/odoo_dataflow_scaffold/actions?workflow=Tests
[codecov]: https://app.codecov.io/gh/bosd/odoo_dataflow_scaffold
[pre-commit]: https://github.com/pre-commit/pre-commit
[ruff badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[ruff project]: https://github.com/charliermarsh/ruff

## Features

**odoo_dataflow_scaffold accelarates** the development of import/export projects using [odoo-data-flow](https://github.com/OdooDataFlow/odoo-data-flow) tools It provides two main functions:

* **Creates** the folders structure and a basic set of files that organize the project.
* **Generates** skeleton code that applies transformations to a client file before importing it into Odoo.


The skeleton code documents the fields thoroughly, eliminating the need to look up their definitions with an external tool. A field analysis automatically suggests to exclude some of them when they shoud not be imported.
Each new skeleton code is fully integrated in the other project files.

## Requirements

- TODO

## Installation

You can install _Odoo_Dataflow_Scaffold_ via [pip] from [PyPI]:


<!-- * From GitHub -->
To install `odoo_dataflow_scaffold` from GitHub, use the following command:

```console
git clone git@github.com:OdooDataFlow/odoo_dataflow_scaffold.git
```

<!-- * From PyPi  
```console
$ pip install odoo_dataflow_scaffold
```
-->



## Usage

Please see the [Command-line Reference] for details.

## Contributing

Contributions are very welcome.
To learn more, see the [Contributor Guide].

## License

Distributed under the terms of the [GPL 3.0 license][license],
_Odoo_Dataflow_Scaffold_ is free and open source software.

## Issues

If you encounter any problems,
please [file an issue] along with a detailed description.

## Credits

This project was generated from [@bosd]'s [uv hypermodern python cookiecutter] template.

[@bosd]: https://github.com/bosd
[pypi]: https://pypi.org/
[uv hypermodern python cookiecutter]: https://github.com/bosd/cookiecutter-uv-hypermodern-python
[file an issue]: https://github.com/bosd/odoo_dataflow_scaffold/issues
[pip]: https://pip.pypa.io/

<!-- github-only -->

[license]: https://github.com/bosd/odoo_dataflow_scaffold/blob/main/LICENSE
[contributor guide]: https://github.com/bosd/odoo_dataflow_scaffold/blob/main/CONTRIBUTING.md
[command-line reference]: https://odoo_dataflow_scaffold.readthedocs.io/en/latest/usage.html
