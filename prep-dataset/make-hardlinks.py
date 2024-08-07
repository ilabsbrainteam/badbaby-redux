from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from shutil import copyfileobj
from subprocess import run
import yaml

from utils import hardlink

dry_run = False
root = Path("/storage/badbaby-redux").resolve()

# logging
outdir = Path("qc").resolve()
outdir.mkdir(exist_ok=True)
logfile = StringIO()
add_to_log = redirect_stdout(logfile)

# read in source → target mappings from the `select-files-from-*.py` scripts
with open("files-from-local.yaml", "r") as fid:
    local_files = yaml.load(fid, Loader=yaml.SafeLoader)
with open("files-from-server.yaml", "r") as fid:
    server_files = yaml.load(fid, Loader=yaml.SafeLoader)
mapping = local_files | server_files

# make hardlinks for the FIF files
for source, target in mapping.items():
    source = Path(source)
    target = Path(target)
    # this guard shouldn't be necessary due to -n flag in hardlink command,
    # but let's be extra careful:
    if not target.is_file():
        hardlink(source, target, dry_run)
    # don't bother telling me if the filesizes are identical
    elif source.stat().st_size != target.stat().st_size:
        with add_to_log:
            print(
                f"FILE SIZE MISMATCH: not linking {source.relative_to(root)} to "
                f"{target.relative_to(root)}"
            )

if not dry_run:
    run(["chgrp", "--recursive", "badbaby", str(root / "data")])

with open(outdir / "log-of-hardlinking.txt", "w") as fid:
    logfile.seek(0)
    copyfileobj(logfile, fid)
logfile.close()
