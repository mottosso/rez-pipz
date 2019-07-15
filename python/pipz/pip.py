"""Install pip-package are rez-package

Algorithm:
    1. Install with pip --install six --target STAGING_DIR
    2. Scan STAGING_DIR for installed packages and report
    3. Convert pip-package requirements to rez-requirements
    4. Convert pip-package to rez-package

"""

from rez.vendor.distlib import DistlibException
from rez.vendor.distlib.database import DistributionPath
from rez.vendor.distlib.markers import interpret
from rez.vendor.distlib.util import parse_name_and_version
from rez.utils.logging_ import print_warning
from rez.package_maker__ import PackageMaker
from rez.config import config
from rez.vendor.six import six
from rez.utils.platform_ import platform_
from rez.utils.filesystem import retain_cwd
from rez.backport.lru_cache import lru_cache

import os
import sys
import stat
import errno
import shutil
import logging
import tempfile
import traceback
import subprocess

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


# As per https://packaging.python.org/
#        specifications/entry-points/#file-format
class CaseSensitiveConfigParser(ConfigParser):
    optionxform = staticmethod(str)


# Public API
__all__ = [
    "install",
    "download",
    "convert",
    "deploy",
]

_basestring = six.string_types[0]
_package_to_distribution = {}
_log = logging.getLogger("pipz")
_pipzdir = os.path.dirname(__file__)
_pythondir = os.path.dirname(_pipzdir)
_rootdir = os.path.dirname(_pythondir)
_shim = os.path.join(_rootdir, "bin", "shim.exe")


def install(names,
            prefix=None,
            release=False,
            variants=None,
            extra_args=None):
    """Convenience function to below functions

    Arguments:
        names (list): pip-formatted package names, e.g. six=1.12
        prefix (str, optional): Absolute path to destination repository
        release (bool, optional): Install onto REZ_RELEASE_PACKAGES_PATH
        variants (list, optional): Override variants detected by WHEEL
        index (str, optional): Override PyPI index. This should point to a
            repository compliant with PEP 503 (the simple repository API)
            or a local directory laid out in the same format.
        extra_args (list, optional): Additional arguments passed to `pip`

    """

    assert prefix is None or isinstance(prefix, _basestring), (
        "%s was not str" % prefix)
    assert isinstance(names, (tuple, list)), "%s was not list or tuple" % names

    tempdir = tempfile.mkdtemp(suffix="-rez", prefix="pip-")

    distributions = download(
        names,
        tempdir=tempdir,
        extra_args=extra_args,
    )

    packagesdir = prefix or (
        config.release_packages_path if release
        else config.local_packages_path
    )

    new, existing = list(), list()
    for dist in distributions:
        package = convert(dist, variants=variants)

        if exists(package, packagesdir):
            existing.append(package)
        else:
            new.append(package)

    if not new:
        return []

    for package in new:
        deploy(package, path=packagesdir)

    shutil.rmtree(tempdir)
    return new


def download(names, tempdir=None, extra_args=None):
    """Gather pip packages in `tempdir`

    Arguments:
        names (list): Names of packages to install, in pip-format,
            e.g. ["six==1"]
        tempdir (str, optional): Absolute path to where pip packages go until
            they've been installed as Rez packages, defaults to the cwd
        extra_args (list, optional): Additional arguments, typically only
            relevant to pip rather than pipz

    Returns:
        distributions (list): Downloaded distlib.database.InstalledDistribution

    Raises:
        OSError: On anything gone wrong with subprocess and pip

    """

    extra_args = extra_args or []

    assert isinstance(names, (list, tuple)), (
        "%s was not a tuple or list" % names
    )
    assert all(isinstance(name, _basestring) for name in names), (
        "%s contained non-string" % names
    )

    tempdir = tempdir or os.getcwd()

    # Build pip commandline
    cmd = [
        "python", "-m", "pip", "install",
        "--target", tempdir,

        # Only ever consider wheels, anything else is ancient
        "--use-pep517",

        # Handle case where the Python distribution used alongside
        # pip already has a package installed in its `site-packages/` dir.
        "--ignore-installed",

        # rez pip users don't have to see this
        "--disable-pip-version-check",
    ]

    for extra_arg in extra_args:
        if extra_arg in cmd:
            print_warning("'%s' argument ignored, used internally" % extra_arg)
            continue
        cmd += [extra_arg]

    cmd += names

    call(cmd)

    distribution_path = DistributionPath([tempdir])
    distributions = list(distribution_path.get_distributions())

    return sorted(
        distributions,

        # Upper-case characters typically come first
        key=lambda d: d.name.lower()
    )


def exists(package, path):
    """Does `distribution` already exists as a Rez-package in `path`?

    Arguments:
        package (rez.Package):
        path (str): Absolute path of where to look

    """

    try:
        variant = next(package.iter_variants())
    except StopIteration:
        return False

    return variant.install(path, dry_run=True) is not None


def convert(distribution, variants=None):
    """Make a Rez package out of `distribution`

    Arguments:
        distribution (distlib.database.InstalledDistribution): Source
        variants (list, optional): Explicitly provide variants, defaults
            to automatically detecting the correct variants using the
            WHEEL metadata of `distribution`.

    """

    name, _ = parse_name_and_version(distribution.name_and_version)
    name = _rez_name(distribution.name[:len(name)])

    # determine variant requirements
    variants_ = variants or []

    if not variants_:
        wheen_fname = os.path.join(distribution.path, "WHEEL")
        with open(wheen_fname) as f:
            variants_.extend(wheel_to_variants(f.read()))

    requirements = _pip_to_rez_requirements(distribution)

    maker = PackageMaker(name)
    maker.version = distribution.version

    if requirements:
        maker.requires = requirements

    if distribution.metadata.summary:
        maker.description = distribution.metadata.summary

    if variants_:
        maker.variants = [variants_]

    maker.commands = '\n'.join([
        "env.PATH.prepend('{root}/bin')",
        "env.PYTHONPATH.prepend('{root}/python')"
    ])

    package = maker.get_package()

    # Store reference for deployment
    _package_to_distribution[package] = distribution

    return package


def deploy(package, path, shim="binary"):
    """Deploy `distribution` as `package` at `path`

    Arguments:
        package (rez.Package): Source package
        path (str): Path to install directory, e.g. "~/packages"

    """

    def make_root(variant, destination_root):
        distribution = _package_to_distribution[package]

        # Store files from distribution for deployment
        files = list()
        for relpath, md5, size in distribution.list_installed_files():
            root_ = os.path.dirname(distribution.path)
            files += [(root_, relpath)]

        for source_root, relpath in files:
            src = os.path.join(source_root, relpath)
            src = os.path.normpath(src)

            if not os.path.exists(src):
                continue

            dst = os.path.join(root, "python", relpath)
            dst = os.path.normpath(dst)

            if not os.path.exists(os.path.dirname(dst)):
                os.makedirs(os.path.dirname(dst))

            shutil.copyfile(src, dst)

        console_scripts = find_console_scripts(distribution)

        if not console_scripts:
            return

        dst = os.path.join(root, "bin")
        dst = os.path.normpath(dst)

        if not os.path.exists(dst):
            os.makedirs(dst)

        for exe, command in console_scripts.items():
            write_console_script(dst, exe, command, shim == "binary")

    variant = next(package.iter_variants())
    variant_ = variant.install(path)

    root = variant_.root
    if make_root and root:
        try:
            os.makedirs(root)
        except OSError as e:
            if e.errno == errno.EEXIST:
                # That's ok
                pass
            else:
                raise

    with retain_cwd():
        os.chdir(root)
        make_root(variant_, root)

    return variant_


def find_console_scripts(distribution):
    """Find entry points from `distribution`

    Every distribution with an entry_point section contains
    a `entry_points.txt` file in ConfigParser format.

    """

    # Specification of this file:
    #     https://packaging.python.org/specifications/
    #     entry-points/#file-format
    fname = os.path.join(
        distribution.path,
        "entry_points.txt"
    )

    try:
        parser = CaseSensitiveConfigParser()
        parser.read(fname)

    # There may not be any entry points
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    scripts = parser._sections.get("console_scripts", {})

    # Generic default on Linux
    scripts.pop("__name__", None)

    return scripts


bat = """\
@echo off
python -u -c "import {module} as m;m.{func}()"
"""

shim = """\
path = python
args = -u -c "import {module} as m;m.{func}()"
"""

sh = """\
#!/usr/bin/env python
import {module} as mod
mod.{func}()
"""


def write_console_script(root, executable, command, binary=True):
    """Write `executable` file for `command` at `root`

    On Windows, shims use a similar mechanism as the Scoop
    package manager; a binary executable written in C that
    accompanied by a .shim file containing name of command
    and arguments. The executable forwards signals such as
    CTRL+C and respects the process hierarchy, killing
    children alongside itself.

    On Linux and MacOS the console scripts are written as
    executable shell scripts, with a #!/use/bin/env bash

    Arguments:
        root (str): Absolute path to where to write executable files
        executable (str): Name of executable file, without suffix,
            e.g. rez or pyblish
        command (str): Module and function pair, e.g. "module:func",
            with no arguments. Same syntax as setup(console_scripts=)
        binary (bool, optional): Windows-only, whether to write a
            .bat script or a binary .exe file

    Example:
        >> write_console_script("~/", "listdir", "os:listdir")

    """

    fname = os.path.join(root, executable)

    try:
        module, func = command.split(":")
    except ValueError:

        if _log.level < logging.INFO:
            traceback.print_exc()

        return sys.stderr.write("Could not write %s\n" % fname)

    if binary:
        shutil.copyfile(_shim, fname + ".exe")
        with open(fname + ".shim", "w") as f:
            f.write(shim.format(**locals()))

    else:
        with open(fname + ".bat", "w") as f:
            f.write(bat.format(**locals()))

    with open(fname, "w") as f:
        f.write(sh.format(**locals()))

    st = os.stat(fname)
    os.chmod(fname, st.st_mode | stat.S_IEXEC)


def wheel_to_variants(wheel):
    """Parse WHEEL file of `distribution` as per PEP427

    https://www.python.org/dev/peps/pep-0427/#file-contents

    Arguments:
        wheel (str): Contents of a WHEEL file

    Returns:
        variants (dict): With keys {"platform", "os", "python"}

    """

    variants = {
        "platform": None,
        "os": None,
        "python": None,
    }

    py = {
        "2": False,
        "3": False,
        "minor": False,
    }

    for line in wheel.splitlines():
        line = line.rstrip()

        if not line:
            # Empty lines are allowed
            continue

        line = line.replace(" ", "")
        key, value = line.lower().split(":")

        if key == "wheel-version":
            if value[0] != "1":
                raise ValueError("Unsupported WHEEL format")

        if key == "root-is-purelib" and value == "false":
            variants["platform"] = platform_name()

        if key == "tag":
            # May occur multiple times
            #
            # Example:
            #   py2-none-any
            #   py3-none-any
            #   cp36-cp36m-win_amd64
            #
            py_tag, abi_tag, plat_tag = value.split("-")
            major_ver = py_tag[2]

            py[major_ver] = True

            if plat_tag != "any":
                # We could convert e.g. `win_amd64` to a Rez platform
                # and os version, such as `platform-windows` and
                # `os-windows.10.0.1800` but it's safe to assume that if
                # this package was provided by pip, it must be specific
                # to the currently running platform and os.

                variants["os"] = os_name()
                variants["platform"] = platform_name()  # e.g. windows

                # Indicate that this week depends on the Python minor version
                # which is true of any compiled Python package.
                py["minor"] = True

    if py["minor"]:
        # Use the actual version from the running Python
        # rather than what's coming out of the the WHEEL
        variants["python"] = python_version()

    elif py["2"] and py["3"]:
        variants["python"] = None

    elif py["2"]:
        variants["python"] = "2"

    elif py["3"]:
        variants["python"] = "3"

    return [
        k + "-" + variants[k]

        # Order is important
        for k in ("platform",
                  "os",
                  "python")

        if variants[k] is not None
    ]


def os_name():
    """Return pip-compatible OS, e.g. windows-10.0 and Debian-7.6"""
    # pip packages are no more specific than minor/major of an os
    # E.g. windows-10.0.18362 -> windows-10.0
    try:
        return ".".join(platform_.os.split(".")[:2])

    except TypeError:
        # A platform_map may have been used to reduce
        # the number of available components, or the
        # OS simply doesn't provide enough, e.g. centos-7
        return platform_.os


def platform_name():
    return platform_.name


@lru_cache()
def python_version():
    """Return major.minor version of Python, prefer current context"""

    import subprocess
    from rez.status import status
    context = status.context

    try:
        # Use supplied Python
        package = context.get_resolved_package("python")
        return ".".join(str(v) for v in package.version[:2])

    except AttributeError:
        # In a context, but no Python was found
        pass

    except IndexError:
        # We'll need this for almost every package on PyPI
        raise IndexError("%s didn't have a minor version" % package.uri)

    # Try system Python
    popen = subprocess.Popen(
        """\
        python -c "import sys;print('.'.join(map(str, sys.version_info[:2])))"
        """,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=10 ** 4,  # Enough to capture the version
        shell=True,
    )

    if popen.wait() == 0:
        version = popen.stdout.read().rstrip()
        return version  # 3.7


@lru_cache()
def pip_version():
    """Return version of pip"""
    import subprocess
    from rez.status import status
    context = status.context

    try:
        # Use supplied Python
        package = context.get_resolved_package("pip")
        return str(package.version)
    except AttributeError:
        # In a context, but no Python was found
        pass

    # Try system Python
    popen = subprocess.Popen(
        "python -c \"import pip;print(pip.__version__)\"",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=10 ** 4,  # Enough to capture the version
        shell=True,
    )

    if popen.wait() == 0:
        version = popen.stdout.read().rstrip()
        return version


def call(command, **kwargs):
    # Use logging level to determine verbosity
    verbose = _log.level < logging.INFO

    if isinstance(command, (tuple, list)):
        command = " ".join(command)

    popen = subprocess.Popen(
        command,
        shell=True,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        **kwargs
    )

    output = list()
    for line in iter(popen.stdout.readline, ""):

        if line.startswith("DEPRECATION"):
            # Mute warnings about Python 2 being deprecated.
            # It's out-of-band for the casual Rez user.
            continue

        output += [line.rstrip()]

        if verbose:
            sys.stdout.write("# " + line)

    popen.wait()

    if popen.returncode != 0:
        command = command if isinstance(command, (list, tuple)) else [command]
        raise OSError(
            # arg1 arg2 -------
            # Some error here
            # ------------------
            "\n".join([
                ("%s " % " ".join(command)).ljust(70, "-"),
                "",
                "\n".join(output),
                "",
                "-" * 70,
            ])
        )


def _rez_name(pip_name):
    return pip_name.replace("-", "_")


def _get_dependencies(requirement):
    requirements = ([requirement] if isinstance(requirement, _basestring)
                    else requirement["requires"])

    result = []
    for package in requirements:
        if "(" in package:
            try:
                name, version = parse_name_and_version(package)
                version = version.replace("==", "")
                name = _rez_name(name)
            except DistlibException:
                n, vs = package.split(' (')
                vs = vs[:-1]
                versions = []
                for v in vs.split(','):
                    package = "%s (%s)" % (n, v)
                    name, version = parse_name_and_version(package)
                    version = version.replace("==", "")
                    versions.append(version)
                version = "".join(versions)
                name = _rez_name(name)

            result.append("-".join([name, version]))
        else:
            name = _rez_name(package)
            result.append(name)

    return result


def _pip_to_rez_requirements(distribution):
    """Convert pip-requirements --> rez-requirements"""

    requirements = []
    for req in (distribution.metadata.run_requires or []):
        if "environment" in req:
            if interpret(req["environment"]):
                requirements += _get_dependencies(req)

        elif "extra" in req:
            # TODO: Handle optional requirements
            # e.g. requests[security]
            pass

        else:
            requirements += _get_dependencies(req)

    return requirements


# Copyright 2013-2016 Allan Johns.
#
# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.
