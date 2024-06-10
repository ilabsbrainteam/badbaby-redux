import re
from collections import defaultdict
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from shutil import copyfileobj

import numpy as np
import pandas as pd
from mne.io import read_info
from mne.utils import set_log_level

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
missing_erms = pd.read_csv(
    outdir / "erm-missing-from-data.csv", header=0, index_col=False
)

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

matched_erm_dates = list()
missing_erm_dates = list()

# look for date matches for sessions missing ERMs
for _, (subj_id, exp, target_date) in missing_erms.iterrows():
    target_date = date.fromisoformat(target_date)
    if target_date in available_erms:
        matching_erm = available_erms[target_date][0].name
        with add_to_log:
            print(f"using {matching_erm} (same-day) as surrogate ERM for {subj_id}")
        matched_erm_dates.append(
            pd.DataFrame(
                dict(date=target_date, recipient=subj_id, exp=exp, donor=matching_erm),
                index=[0],
            )
        )
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
            matched_erm_dates.append(
                pd.DataFrame(
                    dict(date=target_date, recipient=subj_id, exp=exp, donor=nearest),
                    index=[0],
                )
            )
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

matched_erm_dates = pd.concat(matched_erm_dates, ignore_index=True)
matched_erm_dates.sort_values(["recipient", "exp"], inplace=True)
matched_erm_dates.to_csv(outdir / "erm-surrogates.csv", index=False, header=True)

with open(outdir / "log-of-surrogate-erms.txt", "w") as fid:
    logfile.seek(0)
    copyfileobj(logfile, fid)
logfile.close()

missing_erm_dates = list(map(str, sorted(missing_erm_dates)))
with open(outdir / "erm-missing-dates.txt", "w") as fid:
    for _date in missing_erm_dates:
        fid.write(f"{_date}\n")
