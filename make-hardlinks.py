from pathlib import Path
from subprocess import run
import yaml


def hardlink(source, target, dry_run=True):
    """Create target dirs, then hardlink."""
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["cp", "-ln", "--preserve=all", str(source), str(target)]
    if not dry_run:
        run(cmd)


dry_run = True
root = Path(".").resolve()

# first link all prebad.txt files (those don't exist on server, only local)
indir = root / "local-data"
prebads = indir.rglob("bad_*_prebad.txt")
for source in prebads:
    target = root / "data" / source.relative_to(indir)
    hardlink(source, target, dry_run)

# read in source → target mappings from the `select-files-from-*.py` scripts
with open("local.yaml", "r") as fid:
    local_files = yaml.load(fid, loader=yaml.SafeLoader())
with open("server.yaml", "r") as fid:
    server_files = yaml.load(fid, loader=yaml.SafeLoader())
mapping = local_files | server_files

# make hardlinks for the FIF files
for source, target in mapping.items():
    # this guard shouldn't be necessary due to -n flag in hardlink command,
    # but let's be extra careful:
    if not target.is_file():
        hardlink(source, target, dry_run)
    # don't bother telling me if the filesizes are identical
    elif source.stat().st_size != target.stat().st_size:
        print(
            f"FILE SIZE MISMATCH: not linking {source.relative_to(root)} to "
            f"{target.relative_to(root)}"
        )
