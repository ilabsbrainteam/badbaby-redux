import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

outdir = Path("data-qc")  # where summary files will be written

# where to look for the data
root = Path("local-data").resolve()
subj_dirs = sorted(root.glob("bad*"))
subj_ids = [x.name.lstrip("bad_") for x in subj_dirs]
# what kinds of data files do we expect?
expected_files = {
    "prebad.txt": [],
    "mmn_raw.fif": [],
    "am_raw.fif": [],
    "ids_raw.fif": [],
    "erm_raw.fif": [],
}
pattern = f"bad.*({'|'.join(expected_files)})$"

# loop over subject folders, and tally which of the expected file types we find
for _dir in subj_dirs:
    df_row = defaultdict(lambda: False)
    for _fname in (_dir / "raw_fif").iterdir():
        for _kind in expected_files:
            df_row[_kind] |= _fname.name.endswith(_kind)
        if not re.match(pattern, _fname.name):
            print(f"unexpected file: {_fname}")
    for _kind, value in df_row.items():
        expected_files[_kind].append(value)
# aggregate results into a dataframe
result = pd.DataFrame(data=expected_files, index=subj_ids)
result.columns = [re.split(r"_|\.", x)[0] for x in result.columns]
# print some summary output
total = f"Total sessions: {result.shape[0]}"
table = result.sum().to_frame().T.to_string(index=False)
line = "-" * max(len(total), len(table.split("\n")[0]))
print(line)
print(total)
print(line)
print(table)
print(line)
print()

# note which sessions are missing ERMs
missing_erm = result.index[~result["erm"]].to_series().reset_index(drop=True)
missing_erm.to_csv(outdir / "missing-erm.csv", index=False, header=False)

# split subj and session identifiers
result["subj"] = result.index.str.slice(0, -1).astype(int)
result["session"] = result.index.str.slice(-1)
result.reset_index(drop=True, inplace=True)
# save dataframe to disk now, while data is still in "raw" (unaggregated) form
result.to_csv(outdir / "files-originating-from-local-drive.csv")

# remap the boolean column values to session codes "a" or "b"
for column in ("prebad", "mmn", "am", "ids", "erm"):
    result[column] = result["session"].where(result[column], other="")
# aggregate to show which subjs/conds have data from both sessions
result = result.groupby("subj").agg("sum")

total1 = f"Total subjects: {result.shape[0]}"
total2 = f"Subjects with both sessions: {(result["session"] == "ab").sum()}"
title1 = "Subjects with complete data, by condition:"
table1 = (result == "ab").sum().drop("session").to_frame().T.to_string(index=False)
title2 = ("Subjects with complete data for all conditions: "
          f"{(result == "ab").all(axis="columns").sum()}")

line = "-" * max(map(len, (total1, total2, title1, title2, table1.split("\n")[0])))


print(line)
print(total1)
print(total2)
print(line)
print(title1)
print(line)
print(table1)
print(line)
print(title2)
print(line)
