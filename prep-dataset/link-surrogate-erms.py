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
    target_dir = root / f"bad_{recip}" / "raw_fif"
    already_has_erm = bool(len(list(target_dir.glob("*erm_raw.fif"))))
    needs_multiple_erms = (
        len(df.groupby("recipient").get_group(recip)["date"].unique()) > 1
    )
    if already_has_erm or needs_multiple_erms:
        target = target_dir / f"bad_{recip}_{row['exp']}_erm_raw.fif"
    else:
        target = target_dir / f"bad_{recip}_erm_raw.fif"
    run(["cp", "-ln", "--preserve=all", str(source), str(target)])
