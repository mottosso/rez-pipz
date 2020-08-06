import os
import sys
import shutil
import tempfile
import argparse
import subprocess

try:

    # An unfortunate hack..
    # https://stackoverflow.com/questions/52074590/
    # urllib-request-urlopen-ssl-certificate-verify-
    # failed-error-on-windows-vista/52074591#52074591
    from urllib.request import urlopen

    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    def urlretrieve(url, fname):
        with urlopen(url, context=ctx) as u:
            with open(fname, 'wb') as f:
                f.write(u.read())

except ImportError:
    # Support for Python 2.7
    from urllib import urlretrieve

parser = argparse.ArgumentParser()
parser.add_argument("--overwrite", action="store_true")
parser.add_argument("--pip", default="20.2b1")
parser.add_argument("--wheel", default="0.33.4")
parser.add_argument("--setuptools", default="41.0.1")
parser.add_argument("--packaging", default="19.0")

opts = parser.parse_args()


def ask(msg):
    try:
        # Python 2 support
        _input = raw_input
    except NameError:
        _input = input

    try:
        value = _input(msg).lower().rstrip()  # account for /n and /r
        return value in ("", "y", "yes", "ok")
    except EOFError:
        return True  # On just hitting enter
    except KeyboardInterrupt:
        return False


if int(os.getenv("REZ_BUILD_INSTALL")):
    install_dir = os.environ["REZ_BUILD_INSTALL_PATH"]
    exists = os.path.exists(install_dir)

    if exists and os.listdir(install_dir):
        print("Previous install found %s" % install_dir)

        if opts.overwrite or ask("Overwrite existing install? [Y/n] "):
            print("Cleaning existing install %s.." % install_dir)
            shutil.rmtree(install_dir)
        else:
            print("Aborted")
            exit(1)


build_dir = os.environ["REZ_BUILD_PATH"]
python_dir = os.path.join(build_dir, "python")
print("Building into: %s" % build_dir)

root = os.path.dirname(__file__)
for dirname in ("python", "bin"):
    print("Copying %s/.." % dirname)
    shutil.copytree(
        os.path.join(root, dirname),
        os.path.join(build_dir, dirname)
    )

version = None

with open(os.path.join(root, "package.py")) as f:
    for line in f:
        if not line.startswith("version ="):
            continue
        exec(line)
        break


assert version, "Couldn't figure out version from package.py"

# Embed version into Python package
with open(os.path.join(build_dir,
                       "python",
                       "pipz",
                       "__version__.py"), "w") as f:
    f.write("version = \"%s\"" % version)

tempdir = tempfile.mkdtemp()
url = "https://bootstrap.pypa.io/get-pip.py"
get_pip = os.path.join(tempdir, "get-pip.py")
print("Downloading %s.." % url)
urlretrieve(url, get_pip)

print("Installing pip into '%s'.." % python_dir)
try:
    assert subprocess.check_call([
        sys.executable, "-u", "-E", get_pip,
        "pip==%s" % opts.pip,
        "wheel==%s" % opts.wheel,
        "setuptools==%s" % opts.setuptools,
        "packaging==%s" % opts.packaging,
        "--target", python_dir
    ]) == 0

except (subprocess.CalledProcessError, AssertionError):
    sys.stderr.write("Failed\n")

finally:
    shutil.rmtree(tempdir)


if int(os.getenv("REZ_BUILD_INSTALL")):
    print("Installing into '%s'.." % install_dir)

    try:
        shutil.rmtree(install_dir)  # Created by Rez
    except Exception:
        # May not exist
        pass

    shutil.copytree(
        build_dir,
        install_dir,
        ignore=shutil.ignore_patterns(
            "*.pyc",
            "__pycache__"
        )
    )
