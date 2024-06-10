import argparse
import re
from collections import defaultdict
from contextlib import redirect_stdout
from functools import partial
from io import StringIO
from pathlib import Path
from shutil import copyfileobj

import pandas as pd
from mne.io import read_info

# arg parsing
parser = argparse.ArgumentParser(prog="")
parser.add_argument("datadir", choices=("combined", "server", "local", "erm"))
args = parser.parse_args()

# where to look for the data
paths = dict(combined="data", server="server-data", local="local-data", erm="data")
which_data = paths[args.datadir]
root = Path("/storage/badbaby-redux").resolve() / which_data

# where to write logs etc.
outdir = Path("qc").resolve()  # where summary files will be written
outdir.mkdir(exist_ok=True)
logfile = StringIO()
errfile = StringIO()
add_to_log = redirect_stdout(logfile)
add_to_err = redirect_stdout(errfile)

# get subject IDs
subj_dirs = sorted(root.glob("bad*"))
subj_ids = [x.name.lstrip("bad_") for x in subj_dirs]
# what kinds of data files do we expect?
expected_files = {
    "mmn_raw.fif": [],
    "am_raw.fif": [],
    "ids_raw.fif": [],
    "erm_raw.fif": [],
}
pattern = rf"bad_\d{{3}}[ab]?_.*({'|'.join(expected_files)})$"
# loop over subject folders, and tally which of the expected file types we find
for _dir in subj_dirs:
    df_row = defaultdict(lambda: False)
    # handle the one bad folder name in local data
    subdir = "raw_fif" if (_dir / "raw_fif").is_dir() else "151007"
    for _fname in (_dir / subdir).iterdir():
        for _kind in expected_files:
            df_row[_kind] |= _fname.name.endswith(_kind)
        # special case: this one we name `raw2` on purpose
        if not re.match(pattern, _fname.name):
            with add_to_err:
                print(f"unexpected file: {_fname}")
    for _kind, value in df_row.items():
        expected_files[_kind].append(value)
# aggregate results into a dataframe
result = pd.DataFrame(data=expected_files, index=subj_ids)
result.columns = [re.split(r"_|\.", x)[0] for x in result.columns]

# get meas_dates to ensure we have ERMs on the correct days
dates_df = pd.DataFrame([], columns=result.columns)
for tup in result.itertuples():
    _fpath = root / f"bad_{tup.Index}" / "raw_fif"
    for kind in dates_df.columns:
        if getattr(tup, kind):  # skip if file not available
            _fname = f"bad_{tup.Index}_{kind}_raw.fif"
            info = read_info(_fpath / _fname, verbose=False)
            dates_df.loc[tup.Index, kind] = info["meas_date"].date()

# get date mismatches between experimental runs and ERMs
matches_df = pd.DataFrame(
    {
        col: dates_df[col].eq(dates_df["erm"])
        for col in dates_df.drop(columns="erm").columns
    }
)
# save the dates of mismatches. Also captures exp files where ERM is missing entirely.
erm_mismatches = list()
for subj in matches_df.index:
    for exp in matches_df.columns:
        exp_date = dates_df.loc[subj, exp]
        erm_date = dates_df.loc[subj, "erm"]
        if (
            ~matches_df.loc[subj, exp]
            and not pd.isna(exp_date)  # no experimental recording for that subj
        ):
            this_row = dict(subj=subj, exp=exp, date=exp_date)
            erm_mismatches.append(pd.DataFrame(this_row, index=[0]))
erm_mismatches = pd.concat(erm_mismatches, ignore_index=True)
erm_mismatches.to_csv(outdir / f"erm-missing-from-{which_data}.csv", index=False)

# print some summary output
total = f"Total sessions: {result.shape[0]}"
table = result.sum().to_frame().T.to_string(index=False)
line = "-" * max(len(total), len(table.split("\n")[0]))

with add_to_log:
    print(line)
    print(total)
    print(line)
    print(table)
    print(line)
    print()

# split subj and session identifiers
result["subj"] = result.index.str.slice(0, 3).astype(int)
session = result.index.str.slice(3)  # may be "" for some subj-sessions
# fill in session "c" for missing session IDs (timepoints not strictly at 2mo or 6mo)
result["session"] = session.where(cond=session.astype(bool), other="c")
result.reset_index(drop=True, inplace=True)
# save dataframe to disk now, while data is still in "raw" (unaggregated) form
result.to_csv(outdir / f"files-in-{which_data}.csv")

# remap the boolean column values to session codes "a" or "b" or "c"
columns = ["mmn", "am", "ids", "erm"]
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
tmp_df = both.drop(columns="session").sum().to_frame().T
tmp_df["all_conds"] = both.all(axis="columns").sum()
table1 = tmp_df.to_string(index=False)

line = "-" * max(map(len, (total1, total2, title1, table1.split("\n")[0])))

with add_to_log:
    print(line)
    print(total1)
    print(total2)
    print(line)
    print(title1)
    print(line)
    print(table1)
    print(line)

if args.datadir == "erm":
    out_fname = "after-linking-erms.txt"
elif args.datadir == "combined":
    out_fname = "of-combined-data.txt"
else:
    out_fname = f"of-{which_data}.txt"

with open(outdir / f"summary-{out_fname}", "w") as fid:
    logfile.seek(0)
    copyfileobj(logfile, fid)
logfile.close()

with open(outdir / f"unexpected-files-{out_fname}", "w") as fid:
    errfile.seek(0)
    copyfileobj(errfile, fid)
errfile.close()
