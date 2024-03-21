from collections import defaultdict
from datetime import date
from pathlib import Path
from subprocess import run

import numpy as np


def datestring_to_date(datestring):
    """Assumes input in YYMMDD format, for years after 2000."""
    return date(*map(int, (f"20{datestring[:2]}", datestring[2:4], datestring[4:])))


# path stuff
root = Path("..").resolve()
ermsource = root / "server-data"
outdir = root / "data"

subj_dirs = sorted(ermsource.glob("bad*"))

# load the list of subj-sessions that are missing ERMs
with open("data-missing-erm.csv", "r") as fid:
    missing_erms = fid.readlines()
missing_erms = [f"bad_{x.strip()}" for x in missing_erms]


available_erms = defaultdict(list)

# first pass: catalog what dates we have ERMs for
for _dir in subj_dirs:
    for _subdir in _dir.iterdir():
        # skip dirs where date is unknown
        if _subdir.name == "111111":
            continue
        # see if there's an ERM
        scan_date = datestring_to_date(_subdir.name)
        for _fname in _subdir.iterdir():
            if _fname.name.endswith("_erm_raw.fif"):
                available_erms[scan_date].append(_fname)


# second pass: look for date matches for sessions missing ERMs
for subj_id in missing_erms:
    if not (ermsource / subj_id).exists():
        print(f"can't infer scan date for {subj_id} who is missing ERM")
        continue
    for _subdir in (ermsource / subj_id).iterdir():
        # skip dirs where date is unknown
        if _subdir.name == "111111":
            continue
        target_date = datestring_to_date(_subdir.name)
        if target_date in available_erms:
            print(f"same-day surrogate ERM found for {subj_id}: {'/'.join(available_erms[target_date][0].parts[-2:])}")
        else:
            diffs = np.abs(np.array(list(available_erms)) - target_date)
            idx = np.argmin(diffs)
            offset = diffs[idx]
            nearest = available_erms[np.array(list(available_erms))[idx]]
            print(f"no same-day surrogate ERM for {subj_id}; nearest is {offset.days} days ({'/'.join(nearest[0].parts[-2:])})")
