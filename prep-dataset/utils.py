from subprocess import run


def hardlink(source, target, dry_run=True):
    """Create target dirs, then hardlink."""
    target.parent.mkdir(parents=True, exist_ok=True)
    # even with sudo `--preserve=all` doesn't work, so chown too
    cmd = ["cp", "-ln", "--preserve=all", str(source), str(target)]
    if not dry_run:
        run(cmd)
