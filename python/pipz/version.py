
try:
    from __version__ import version

except ImportError:
    import os
    repo = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    fname = os.path.join(repo, "package.py")
    version = "0.0"

    try:
        with open(fname) as f:
            for line in f:
                if not line.startswith("version ="):
                    continue

                exec(line)
                break
    except IOError:
        raise
        pass
