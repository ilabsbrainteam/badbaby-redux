from pathlib import Path
from subprocess import run

import pandas as pd


def hardlink(source, target, dry_run=True):
    """Create target dirs, then hardlink."""
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["cp", "-ln", "--preserve=all", str(source), str(target)]
    if not dry_run:
        run(cmd)


root = Path("..").resolve() / "data"

df = pd.read_csv("surrogate-erms.csv", index_col=False)

for _, row in df.iterrows():
    donor_file = row["donor"]
    donor = "_".join(donor_file.split("_")[:2])
    recip = row["recipient"]
    source = root / donor / "raw_fif" / donor_file
    target = root / recip / "raw_fif" / f"{recip}_erm_raw.fif"
    hardlink(source, target, dry_run=False)
