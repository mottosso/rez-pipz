<img width=500 src=https://user-images.githubusercontent.com/2152766/59205156-2eecb500-8b9a-11e9-8ad9-2ef1e167b7b8.png>

Install anything from [PyPI](https://pypi.org/) as a Rez package.

**See also**

- [rez-scoopz](https://github.com/mottosso/rez-scoopz)

<br>

### Features

- [x] **Large selection** Install any of the [180,000+ available packages](https://pypi.org/) from Scoop, like `python` and `git`
- [x] **Try before you buy** Like `apt-get` and `yum`, no packages are actually installed until you've witnessed and confirmed what Scoop comes up with, including complex dependencies.
- [x] **Skip existing**
- [x] **Dependencies included** Python libraries may reference other libraries, which reference additional libraries and so forth. Pipz handles all of that, whilst keeping track of which dependencies you already have in your package repository.
- [x] **Minimal variants** Only make variants for packages that need it, e.g. universal libraries have zero variants, whereas compiled binaries require `arch`, `os` and `platform`. This applies to individual packages regardless of whether they are indirect requirements to a requested package.
- [x] **Zero-compilation** Every package is installed as a [wheel](https://pythonwheels.com/), which is how package authors distributes pre-compiled resources straight to your system.
- [ ] **Pip Scripts to Rez Executables** Some libraries ship with "scripts" or "entry_points" that provide a short-hand for an embedded Python function, such as `pip.exe`. These are typically refer to their parent Python process via absolute path which is a problem if you wanted to provide a different Python package alongside it using Rez. To work around this, Pipz makes this reference relative rather than absolute, such that you can say `rez env pip python-3.7` and use the provided Python with `pip` rather than whichever executable `pip.exe` happened to be built with.

> An avid user of `rez pip`? See [FAQ](#faq)

<br>

### Installation

This repository is a Rez package, here's how you can install it.

```bash
$ git clone https://github.com/mottosso/rez-pipz.git
$ cd rez-pipz
$ rez build --install
```

<br>

### Usage

![pipz](https://user-images.githubusercontent.com/2152766/59216542-bbf03800-8bb3-11e9-85a0-421df2b85f37.gif)

`pipz` is used like any other Rez package, and comes with a handy `install` executable for convenient access.

```bash
$ rez env pipz -- install python
$ rez env python -- python --version
Python 3.7.3
```

Which is the equivalent of calling..

```bash
$ rez env pipz
> $ install python
```

And, for the advanced user, it may also be used as a Python package. Note that it requires Rez itself to be present as a package, along with a copy of Python that isn't coming from Rez.

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
| .--v-------- Scoop ---------o--. |
| |                              | |
| |                              | |
| |                              | |
| |                              | |
| |______________________________| |
|                                  |
`----------------------------------`

```

<br>
