import re
from collections import defaultdict
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from shutil import copyfileobj

import numpy as np
from mne.utils import set_log_level
from mne.io import read_info

# config
set_log_level("WARNING")
erm_days_threshold = 2  # if no same-day ERM, how many days before/after to look?


def get_meas_date(filepath):
    info = read_info(filepath)
    return info["meas_date"].date()


# path stuff
root = Path("/storage/badbaby-redux").resolve()
ermsource = root / "data"
subj_dirs = sorted(ermsource.glob("bad_*"))

# where to write logs
outdir = Path("qc").resolve()  # where summary files will be written
outdir.mkdir(exist_ok=True)
logfile = StringIO()
add_to_log = redirect_stdout(logfile)

# load the list of subj-sessions that are missing ERMs
with open(outdir / "erm-missing-from-data.csv", "r") as fid:
    missing_erms = fid.readlines()
missing_erms = [f"bad_{x.strip()}" for x in missing_erms]


available_erms = defaultdict(list)
pattern = r".*_erm(_raw)?.fif$"
# catalog what dates we have ERMs for
for _dir in subj_dirs:
    # see if there's an ERM recorded specifically for this project
    for _fname in (_dir / "raw_fif").iterdir():
        if re.match(pattern, _fname.name):
            # don't rely on the datestring in the folder; load the file metadata
            scan_date = get_meas_date(_fname)
            available_erms[scan_date].append(_fname)
# see if there's an ERM from a concurrent project
for _fname in (root / "extra-data").iterdir():
    if re.match(pattern, _fname.name):
        scan_date = get_meas_date(_fname)
        available_erms[scan_date].append(_fname)

matched_erm_dates = ["date,recipient,donor"]
missing_erm_dates = list()

# look for date matches for sessions missing ERMs
for subj_id in missing_erms:
    target_date = None
    # assume all recordings for a "session" are from the same day
    for _fname in (ermsource / subj_id / "raw_fif").glob("*.fif"):
        target_date = get_meas_date(_fname)
        break
    assert target_date is not None, target_date
    if target_date in available_erms:
        matching_erm = available_erms[target_date][0].name
        with add_to_log:
            print(f"using {matching_erm} (same-day) as surrogate ERM for {subj_id}")
        matched_erm_dates.append(f"{target_date},{subj_id},{matching_erm}")
    else:
        available_erm_dates = np.array(list(available_erms))
        diffs = available_erm_dates - target_date
        idx = np.argmin(np.abs(diffs))
        timedelta = diffs[idx]
        nearest = available_erms[available_erm_dates[idx]][0].name
        n_days = np.abs(timedelta.days)
        _s = "s" if n_days > 1 else ""
        bef_aft = "before" if np.sign(timedelta.days) < 0 else "after"
        if n_days <= erm_days_threshold:
            matched_erm_dates.append(f"{target_date},{subj_id},{nearest}")
            with add_to_log:
                print(
                    f"using {nearest} ({n_days} day{_s} {bef_aft}) "
                    f"as surrogate ERM for {subj_id}"
                )
        else:
            with add_to_log:
                print(
                    f"no acceptable surrogate ERM for {subj_id}; threshold is "
                    f"{erm_days_threshold} day{'s' if erm_days_threshold > 1 else ''} "
                    f"and nearest is {n_days} day{_s} {bef_aft} ({nearest})"
                )
            missing_erm_dates.append(target_date)

with open(outdir / "log-of-surrogate-erms.txt", "w") as fid:
    logfile.seek(0)
    copyfileobj(logfile, fid)
logfile.close()

missing_erm_dates = list(map(str, sorted(missing_erm_dates)))
with open(outdir / "erm-missing-dates.txt", "w") as fid:
    for _date in missing_erm_dates:
        fid.write(f"{_date}\n")

with open(outdir / "erm-surrogates.csv", "w") as fid:
    for line in matched_erm_dates:
        fid.write(f"{line}\n")
