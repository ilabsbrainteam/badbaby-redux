from subprocess import run


def hardlink(source, target, dry_run=True):
    """Create target dirs, then hardlink."""
    target.parent.mkdir(parents=True, exist_ok=True)
    # even with sudo `--preserve=all` doesn't work, so chown too
    cmd = ["cp", "-ln", "--preserve=all", str(source), str(target)]
    if not dry_run:
        run(cmd)


def load_prebads(fpath):
    # load the prebads (if present)
    if fpath.is_file():
        with open(fpath, "r") as fid:
            prebads = fid.readlines()
        assert len(prebads) == 1, (
            f"expected {fpath.name} to be 1-line space-separated file, "
            f"found {len(prebads)} lines"
        )
        return prebads[0].split()
    else:
        return list()
