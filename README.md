![image](https://user-images.githubusercontent.com/2152766/59871191-d8982700-938e-11e9-88fe-33249483480d.png)

[![Build Status](https://mottosso.visualstudio.com/rez-pipz/_apis/build/status/mottosso.rez-pipz?branchName=master)](https://mottosso.visualstudio.com/rez-pipz/_build/latest?definitionId=6&branchName=master)

Install anything from [PyPI](https://pypi.org/) as a Rez package.

**See also**

- [rez-scoopz](https://github.com/mottosso/rez-scoopz)

<br>

### Features

![pipzdemo](https://user-images.githubusercontent.com/2152766/60382932-5086e100-9a62-11e9-8ecb-f5e4a7372c78.gif)

- [x] **Large selection** Install any of the [180,000+ available packages](https://pypi.org/) from PyPI like Qt.py and Pyblish
- [x] **Try before you buy** Like `apt-get` and `yum`, no packages are actually installed until you've witnessed and confirmed what Scoop comes up with, including complex dependencies.
- [x] **Skip existing**
- [x] **Dependencies included** Python libraries may reference other libraries, which reference additional libraries and so forth. Pipz handles all of that, whilst keeping track of which dependencies you already have in your package repository.
- [x] **Minimal variants** Only make variants for packages that need it, e.g. universal libraries have zero variants, whereas compiled binaries require `arch`, `os` and `platform`. This applies to individual packages regardless of whether they are indirect requirements to a requested package.
- [x] **Zero-compilation** Every package is installed as a [wheel](https://pythonwheels.com/), which is how package authors distributes pre-compiled resources straight to your system.
- [x] **Pip Scripts to Rez Executables** Some libraries ship with "scripts" or "entry_points" that provide a short-hand for an embedded Python function, such as `pip.exe`. These are typically refer to their parent Python process via absolute path which is a problem if you wanted to provide a different Python package alongside it using Rez. To work around this, Pipz makes this reference relative rather than absolute, such that you can say `rez env pip python-3.7` and use the provided Python with `pip` rather than whichever executable `pip.exe` happened to be built with.
- [x] [**Pip to Rez Version Conversion**](https://github.com/mottosso/rez-pipz/issues/1) The pip version syntax is similar to Rez but differ in subtle ways, such as not supporting the `!=` operator. Pipz safely converts these into Rez-qualified versions for your packages.
  - Markers a.k.a. Conditional requirements, e.g. `"PySide; python_version<'3'"`
  - Complex metadata, e.g. `requires` and `python_requires`, including PyQt5-5.12+
  - Not-requirements, e.g. `urllib3!=3.11`
- [ ] **Rez to Pip Version Conversion** Request packages from PyPI using Rez's requires-syntax, such as `pyblish_base-1.8.0` in place of `pyblish-base==1.8.0`. That way, no matter the package managed you use, such as [rez-scoopz](https://github.com/mottosso/rez-scoopz) the syntax remains consistent with Rez. Less to learn!

> An avid user of `rez pip`? See [FAQ](#faq)

<br>

### Installation

**Prerequisites**

- `python-2.7,<4`
- `rez-2.29+`

This repository is a Rez package, here's how you can install it.

```bash
$ git clone https://github.com/mottosso/rez-pipz.git
$ cd rez-pipz
$ rez build --install
```

<br>

### Usage

`pipz` is used like any other Rez package, and comes with a handy `install` executable for convenient access.

```bash
$ rez env pipz -- install bleeding-rez
$ rez env python-3.7 bleeding_rez
> $ python -m rez --version
2.31.0
```

Which is the equivalent of calling..

```bash
$ rez env pipz
> $ install bleeding-rez
```

Per default, `pipz` will install using the latest version of any available `python` package, such as `3.7`. To install using a specific version, include this version in the request.

```bash
$ rez env python-2.7 pipz -- install six
# Installing `six` using Python 2.7
```

For the advanced user, `pipz` may also be used as a Python package. Note that it requires Rez itself to be present as a package, along with a copy of Python that isn't coming from Rez.

```bash
$ rez env pipz -- python
>>> import pipz
>>> pipz.install("six")
```

> Try before I buy?

Prior to creating a package and polluting your package repository, packages are prepared and presented to you for confirmation.

```bash
$ rez pip --install mkdocs
Using python-2.7
Using pip-19.1
Reading package lists... ok - 16.73s
Discovering existing packages... ok - 0.10s
The following NEW packages will be installed:
  Jinja2            2.10.1
  livereload        2.6.1
  Markdown          3.1.1
  mkdocs            1.0.4
  PyYAML            5.1.1    platform-windows/os-windows-10.0/python-2.7
  singledispatch    3.4.0.3
  tornado           5.1.1    platform-windows/os-windows-10.0/python-2.7
The following packages will be SKIPPED:
  backports_abc     0.5
  Click             7.0
  futures           3.2.0    python-2
  MarkupSafe        1.1.1    platform-windows/os-windows-10.0/python-2.7
  setuptools        41.0.1
  six               1.12.0
Packages will be installed to C:\Users\manima\packages
After this operation, 13.51 mb will be used.
Do you want to continue? [Y/n] y
(1/7) Installing Jinja2-2.10.1... ok
(2/7) Installing livereload-2.6.1... ok
(3/7) Installing Markdown-3.1.1... ok
(4/7) Installing mkdocs-1.0.4... ok
(5/7) Installing PyYAML-5.1.1... ok
(6/7) Installing singledispatch-3.4.0.3... ok
(7/7) Installing tornado-5.1.1... ok
7 installed, 6 skipped
Completed in 29.37s
```

> How does this work?

```bash
$ rez env python rez pipz
> $ python -m pipz --help
usage: __main__.py [-h] [--verbose] [--release] [--prefix PATH] [-y] [-q]
                   request

positional arguments:
  request        Packages to install, e.g. python curl

optional arguments:
  -h, --help     show this help message and exit
  --verbose      Include Scoop output amongst pipz messages.
  --release      Write to REZ_RELEASE_PACKAGES_PATH
  --prefix PATH  Write to this exact path
  -y, --yes      Do not ask to install, just do it
  -q, --quiet    Do not print anything to the console
```

> Search?

The original `pip` is included in the package, so you can either use it explicitly.

```bash
$ rez env pipz -- python -m pip search six
```

Or use the wrapper which does the same thing.

```bash
rez env pipz -- search six
django-six (1.0.4)          - Django-six &#8212;&#8212; Django Compatibility Library
six (1.12.0)                - Python 2 and 3 compatibility utilities
six-web (1.0.1)             - Micro python web framework
plivo-six (0.11.5)          - Plivo Python library
py-dom-xpath-six (0.2.3)    - XPath for DOM trees
dots-editor (0.3.7)         - A six-key brailler emulator written in python.
pymosa (0.0.1)              - Readout of up to six Mimosa26 silicon detector planes.
py3compat (0.4)             - Small Python2/3 helpers to avoid depending on six.
affine6p-cstest (0.8.1)     - To calculate affine transformation parameters with six free parameters.
sixgill (0.2.4)             - six-frame genome-inferred libraries for LC-MS/MS
bvcopula (0.9.1)            - Probability and sampling functions for six common seen bivariate copulas
nine (1.0.0)                - Python 2 / 3 compatibility, like six, but favouring Python 3
plonetheme.solemnity (0.7)  - An installable theme for Plone 3.0 based on the solemnity theme by Six Shooter Media.
sixer (1.6.1)               - Add Python 3 support to Python 2 applications using the six module.
Sublimescheme (1.0.7)       - Easily create a Sublime text Color Scheme with as little as six lines of code
momentx (0.2.3)             - A lightweight wrapper around datetime with a focus on timezone handling and few dependencies (datetime, pytz and six).
git-clog (0.2.3)            - git-clog outputs the commit graph of the current Git repository and colorizes commit symbols by interpreting the first six commit hash digits as an RGB color value.
```

<br>

### FAQ

> But Rez already ships with `rez pip --install`?

It does, however..

1. **Overly specific** Limits each Python package to your exact hardware and OS version, e.g. `windows-10.0.1803` despite being universal or compiled to work with almost any version a given OS. This leads to a large number of duplicated installations and a broken install whenever you OS is patched.
3. **No try-before-you-buy** - A Python package like `mkdocs` has 10+ dependencies, all of which are installed (to your exact OS version) without warning.
2. **Build everything** Including libraries that ship with binaries on PyPI such as PySide, which requires a relevant version of Visual Studio or `gcc` or the like.
4. **Backwards compatible** Broken as it is, it needs to remain backwards compatible and thus cannot be improved.
1. **No scripts** Such as `pip.exe`. These are excluded.
1. **No extra arguments** Using `-r` for `requirements.txt` with your install? That's unfortunate. Only explicitly supported arguments are passed along.

**See also**

- https://github.com/nerdvegas/rez/issues/612
- https://github.com/nerdvegas/rez/pull/614

> How does this work?

Packages from PyPI are installed to a temporary location using `pip install --target`, and later converted into Rez packages once dependencies, downloads and unpacking is taken care of by native `pip`.

```
$ rez env pipz -- install six
     |
     |                        .-------------------> ~/packages/six/1.2
     |                        |
.----o-------- pipz ----------o----.
|    |                        |    |
| .--v-------- pip -----------o--. |
| |                              | |
| |                              | |
| |                              | |
| |                              | |
| |______________________________| |
|                                  |
`----------------------------------`

```

<br>
