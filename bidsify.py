"""Create BIDS folder structure for "badbaby" data."""

from collections import defaultdict
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
    module="mne"
)

# path stuff
root = Path().resolve()
orig_data = root / "data"
bids_root = root / "bids-data"

bids_path = BIDSPath(root=bids_root, datatype="meg", suffix="meg", extension=".fif")

# surrogate ERMs (same recording date)
erm_df = pd.read_csv("qc/surrogate-erms.csv", comment="#")
erm_map = {need: have for _, (have, need) in erm_df.iterrows()}

# bad/corrupt files
with open("qc/bad-files.yaml", "r") as fid:
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

    # find the ERM file
    erm_files = list(data_folder.glob("*_erm_raw.fif"))
    this_erm_file = None
    if len(erm_files):
        assert len(erm_files) == 1  # there shouldn't ever be 2 ERMs for the same run
        this_erm_file = erm_files[0]
    elif full_subj in erm_map:
        surrogate = erm_map[full_subj]
        this_erm_file = orig_data / surrogate / "raw_fif" / f"{surrogate}_erm_raw.fif"
    if this_erm_file is None:
        print(f"No ERM file found for subject {subj}")
        erm = None
    elif this_erm_file.name in bad_files:
        print(f"ERM file found for subject {subj}, but the file is corrupted")
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
                bids_path.update(task=task_name, session=session, subject=subj)
                write_raw_bids(
                    raw=raw,
                    bids_path=bids_path,
                    empty_room=erm,
                    overwrite=True,  # TODO if 2 ERMs on one day, this may clobber?
                )

print_dir_tree(bids_root)
