import argparse
import re
from collections import defaultdict
from functools import partial
from pathlib import Path

import pandas as pd

parser = argparse.ArgumentParser(prog="",)
parser.add_argument("datadir", choices=("munged", "server", "local"))
args = parser.parse_args()

# where to look for the data
paths = dict(munged="data", server="server-data", local="local-data")
which_data = paths[args.datadir]
root = Path("..").resolve() / which_data

outdir = Path(".")  # where summary files will be written

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
missing_erm.to_csv(outdir / f"{which_data}-missing-erm.csv", index=False, header=False)

# split subj and session identifiers
result["subj"] = result.index.str.slice(0, 3).astype(int)
session = result.index.str.slice(3)  # may be "" for some subj-sessions
# fill in session "c" for missing session IDs (timepoints not strictly at 2mo or 6mo)
result["session"] = session.where(cond=session.astype(bool), other="c")
result.reset_index(drop=True, inplace=True)
# save dataframe to disk now, while data is still in "raw" (unaggregated) form
result.to_csv(outdir / f"files-in-{which_data}.csv")

# remap the boolean column values to session codes "a" or "b" or "c"
columns = ["prebad", "mmn", "am", "ids", "erm"]
for column in columns:
    result[column] = result["session"].where(cond=result[column], other="")
# aggregate to show which subjs/conds have data from both sessions
result = result.groupby("subj").agg("sum")
# ensure sessions are recorded as "abc" (not e.g. "cab")
columns.append("session")
result[columns] = result[columns].map(lambda x: "".join(sorted(x)))

# check which subjs have both sessions a & b
both = result.map(partial(str.startswith, "ab"))

total1 = f"Total subjects: {result.shape[0]}"
total2 = f"Subjects with *some* data from both sessions: {both['session'].sum()}"
title1 = "Subjects with complete data (sessions a & b), by condition:"
table1 = both.drop(columns="session").sum().to_frame().T.to_string(index=False)
title2 = ("Subjects with complete data for all conditions: "
          f"{both.all(axis="columns").sum()}")

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
