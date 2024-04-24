"""Create BIDS folder structure for "badbaby" data."""

from datetime import date
from pathlib import Path
from warnings import filterwarnings
import yaml

import mne
import pandas as pd
from mne_bids import (
    BIDSPath,
    print_dir_tree,
    write_meg_calibration,
    write_meg_crosstalk,
    write_raw_bids,
)


def _get_date_from_dir_path(dir_path: Path) -> date:
    """Extract date code from the sub-folder name."""
    date_code = dir_path.parts[-1]
    return date(
        year=2000 + int(date_code[:2]),
        month=int(date_code[2:4]),
        day=int(date_code[4:]),
    )


# suppress messages about IAS / MaxShield
mne.set_log_level("WARNING")
filterwarnings(
    action="ignore",
    message="This file contains raw Internal Active Shielding data",
    category=RuntimeWarning,
    module="mne",
)

# path stuff
root = Path("/storage/badbaby-redux").resolve()
orig_data = root / "data"
bids_root = root / "bids-data"
cal_dir = root / "calibration"
outdir = Path("qc").resolve()

bids_path = BIDSPath(root=bids_root, datatype="meg", suffix="meg", extension=".fif")

# init logging (erase old log file)
erm_log = outdir / "log-of-ERM-issues-BIDS.txt"
with open(erm_log, "w") as fid:
    pass

# surrogate ERMs (same recording date)
erm_df = pd.read_csv("qc/erm-surrogates.csv", index_col=False)
erm_map = {need: have for _, (date, need, have) in erm_df.iterrows()}

# bad/corrupt files
with open("bad-files.yaml", "r") as fid:
    bad_files = yaml.load(fid, Loader=yaml.SafeLoader)

# tasks
tasks = dict(
    am="AmplitudeModulatedTones",
    ids="InfantDirectedSpeech",
    mmn="SyllableMismatchNegativity",
)

read_raw_kw = dict(allow_maxshield=True, preload=False)

# classify raw files by "task" from the filenames
for data_folder in orig_data.rglob("bad_*/raw_fif/"):
    # extract the subject ID
    full_subj = data_folder.parts[-2]
    subj = full_subj.lstrip("bad_")
    if subj.endswith("a"):
        session = "a"
    elif subj.endswith("b"):
        session = "b"
    else:
        session = "c"
    # BIDS requires subj to be a string, but cast to int as a failsafe first
    subj = str(int(subj[:3]))

    # write the fine-cal and crosstalk files (once per subject/session)
    bids_path.update(session=session, subject=subj)
    write_meg_calibration(cal_dir / "sss_cal.dat", bids_path=bids_path)
    write_meg_crosstalk(cal_dir / "ct_sparse.fif", bids_path=bids_path)

    # find the ERM file
    erm_files = list(data_folder.glob("*_erm_raw.fif"))
    this_erm_file = None
    if len(erm_files) > 1:
        with open(erm_log, "a") as fid:
            fid.write(f"Found {len(erm_files)} ERM files for subj {full_subj}\n")
        this_erm_file = erm_files[0]
    if this_erm_file is None:
        with open(erm_log, "a") as fid:
            fid.write(f"No ERM file found for subject {subj}\n")
        erm = None
    elif this_erm_file.name in bad_files:
        with open(erm_log, "a") as fid:
            fid.write(f"ERM file found for subject {subj}, but the file is corrupted\n")
        erm = None
    else:
        erm = mne.io.read_raw_fif(this_erm_file, **read_raw_kw)

    # classify the raw files by task, and write them to the BIDS folder
    for raw_file in data_folder.iterdir():
        if raw_file.name in bad_files:
            continue
        for task_code, task_name in tasks.items():
            if task_code in raw_file.name:
                # load the data, then re-write it in the BIDS folder tree
                raw = mne.io.read_raw_fif(raw_file, **read_raw_kw)
                bids_path.update(task=task_name)
                write_raw_bids(
                    raw=raw,
                    bids_path=bids_path,
                    empty_room=erm,
                    overwrite=True,
                )

print_dir_tree(bids_root)
