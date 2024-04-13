import re
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
from mne.utils import set_log_level
from mne.io import read_info

set_log_level("WARNING")


def get_meas_date(filepath):
    info = read_info(filepath)
    return info["meas_date"].date()


# path stuff
root = Path("..").resolve()
ermsource = root / "data"

subj_dirs = sorted(ermsource.glob("bad_*"))

# load the list of subj-sessions that are missing ERMs
with open("data-missing-erm.csv", "r") as fid:
    missing_erms = fid.readlines()
missing_erms = [f"bad_{x.strip()}" for x in missing_erms]


available_erms = defaultdict(list)

# first pass: catalog what dates we have ERMs for
for _dir in subj_dirs:
    # see if there's an ERM
    for _fname in (_dir / "raw_fif").iterdir():
        if re.match(r".*_erm(_raw)?.fif$", _fname.name):
            # don't rely on the datestring in the folder; load the file metadata
            scan_date = get_meas_date(_fname)
            available_erms[scan_date].append(_fname)


matched_erm_dates = ["date,recipient,donor"]
missing_erm_dates = list()

# second pass: look for date matches for sessions missing ERMs
for subj_id in missing_erms:
    for _fname in (ermsource / subj_id / "raw_fif").glob("*.fif"):
        target_date = get_meas_date(_fname)

        break
    if target_date in available_erms:
        matching_erm = available_erms[target_date][0].name
        print(f"same-day surrogate ERM found for {subj_id}: {matching_erm}")
        matched_erm_dates.append(f"{target_date},{subj_id},{matching_erm}")
    else:
        diffs = np.abs(np.array(list(available_erms)) - target_date)
        idx = np.argmin(diffs)
        offset = diffs[idx]
        nearest = available_erms[np.array(list(available_erms))[idx]]
        print(f"no same-day surrogate ERM for {subj_id}; nearest is {offset.days} days ({'/'.join(nearest[0].parts[-2:])})")
        missing_erm_dates.append(target_date)

missing_erm_dates = list(map(str, sorted(missing_erm_dates)))
with open("missing_erm_dates.txt", "w") as fid:
    for _date in missing_erm_dates:
        fid.write(f"{_date}\n")

with open("surrogate-erms.csv", "w") as fid:
    for line in matched_erm_dates:
        fid.write(f"{line}\n")
