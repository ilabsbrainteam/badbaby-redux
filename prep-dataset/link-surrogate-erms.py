from pathlib import Path
from subprocess import run

import pandas as pd


root = Path("/storage/badbaby-redux").resolve() / "data"

df = pd.read_csv(Path("qc") / "erm-surrogates.csv", index_col=False)

for _, row in df.iterrows():
    donor_file = row["donor"]
    if donor_file.startswith("bad_"):
        donor = "_".join(donor_file.split("_")[:2])
        source = root / donor / "raw_fif" / donor_file
    else:
        source = root / ".." / "extra-data" / donor_file
    recip = row["recipient"]
    target = root / recip / "raw_fif" / f"{recip}_erm_raw.fif"
    run(["cp", "-ln", "--preserve=all", str(source), str(target)])
