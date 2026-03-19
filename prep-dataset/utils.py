import functools
from subprocess import check_call, check_output


@functools.lru_cache()
def _get_cp_args():
    output = check_output(["cp", "--version"]).decode("utf-8")
    ver = float(output.splitlines()[0].split()[-1])  # e.g., 9.8
    if ver < 9:
        return ["--no-clobber"]
    else:
        return ["--update=none"]


def hardlink(source, target, dry_run=True):
    """Create target dirs, then hardlink."""
    target.parent.mkdir(parents=True, exist_ok=True)
    # even with sudo `--preserve=all` doesn't work, so chown too
    # Need to triage
    cmd = ["cp", "-l"] + _get_cp_args() + [str(source), str(target)]
    if not dry_run:
        check_call(cmd)


tasks = dict(
    am="AMTone",
    ids="InfDir",
    mmn="SylMMN",
)
