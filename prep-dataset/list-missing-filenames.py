from pathlib import Path

import pandas as pd

outdir = Path("qc").resolve()
df = pd.read_csv(outdir / "files-in-data.csv", index_col=0)

with open(outdir / "files-missing.txt", "w") as fid:
    for _, row in df.iterrows():
        subj = row["subj"]
        session = row["session"] if row["session"] in ("a", "b") else ""
        for kind in ("mmn", "am", "ids", "erm"):
            if not row[kind]:
                fname = f"bad_{subj}{session}_{kind}_raw.fif"
                fid.write(f"{fname}\n")
