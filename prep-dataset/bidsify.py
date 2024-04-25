"""Create BIDS folder structure for "badbaby" data."""

import json
from ast import literal_eval
import datetime
from pathlib import Path
from warnings import filterwarnings
import yaml

import numpy as np
import mne
from mnefun import extract_expyfun_events
from mne_bids import (
    BIDSPath,
    print_dir_tree,
    write_meg_calibration,
    write_meg_crosstalk,
    write_raw_bids,
)
import pandas as pd
from pytz import timezone

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
outdir = root / "prep-dataset" / "qc"

bids_path = BIDSPath(root=bids_root, datatype="meg", suffix="meg", extension=".fif")

# init logging (erase old log files)
erm_log = outdir / "log-of-ERM-issues-BIDS.txt"
score_log = outdir / "log-of-scoring-issues-BIDS.txt"
for log in (erm_log, score_log):
    with open(log, "w") as fid:
        pass

# offsets to disambiguate event IDs from the 3 different experiments
event_offsets = dict(
    am=100,
    ids=2000,
    mmn=30000,
)


def parse_tab_values(value):
    try:
        return float(value)
    except ValueError:
        if value == "[ nan]":
            return np.nan
        elif value.startswith("["):
            return literal_eval(value)[0]
    return value


def score(events, subj, exp_type, meas_date):
    """Convert sequences of 1,4,8 event codes into meaningful trial types."""
    tab_dir = root / "expyfun-logs"
    tabs = sorted(tab_dir.glob(f"{subj}_*.tab"))
    matched_tabs = dict()
    # find the correct .tab file
    for tab in tabs:
        # make sure date matches in filename
        date = tab.name.split("_")[1].split(" ")[0]
        if date != str(meas_date.date()):
            continue
        # read the file metadata (first line of file)
        with open(tab, "r") as fid:
            header = fid.readline()
        metadata = json.loads(header.lstrip("# ").rstrip().replace("'", '"'))
        # make sure metadata matches what we want
        match = dict(IDS="ids", tone="am", syllable="mmn")
        if match[metadata["exp_name"]] != exp_type:
            continue
        assert metadata["participant"] == subj
        pattern = "%Y-%m-%d %H_%M_%S"
        if "." in metadata["date"]:
            pattern += ".%f"
        tab_date = datetime.datetime.strptime(metadata["date"], pattern).replace(
            tzinfo=timezone("US/Pacific")
        )
        time_diff = tab_date - meas_date
        if np.abs(time_diff) > datetime.timedelta(minutes=60):
            continue
        # load the .tab file
        df = pd.read_csv(tab, comment="#", sep="\t")
        # convert pandas-unparseable values into something intelligible
        df["value"] = df["value"].map(parse_tab_values)
        matched_tabs[time_diff] = df
    # see how many matches we got
    if len(matched_tabs) != 1:
        with open(score_log, "a") as fid:
            fid.write(
                f"{len(matched_tabs)} matching TAB files found for subj {subj} "
                f"task {tasks[exp_type]}\n"
            )
    if len(matched_tabs):
        which = np.argmin(np.abs(list(matched_tabs)))
        this_tab = matched_tabs[list(matched_tabs)[which]]
    # convert expyfun trial_id to event code
    # this mapping comes from the original experiment run files (`mmn_expyfun.py`)
    trial_id_map = {
        "Dp01bw6-rms": 2,  # midpoint standard
        "Dp01bw1-rms": 3,  # ba endpoint
        "Dp01bw10-rms": 4,  # wa endpoint
    }
    expyfun_ids = this_tab["value"].loc[this_tab["event"] == "trial_id"]
    offset = event_offsets[exp_type]
    if exp_type == "mmn":
        expyfun_ids = expyfun_ids.map(trial_id_map) + offset
    elif exp_type == "am":
        # all trials had same TTL ID of "2"
        expyfun_ids = np.full_like(expyfun_ids, 2 + offset, dtype=int)
    elif exp_type == "ids":
        # TTL IDs ranged from 0-4
        expyfun_ids += offset + 1
    else:
        raise ValueError(f'Unrecognized experiment type "{exp_type}"')
    assert np.array_equal(events[:, -1], expyfun_ids)
    return events


# surrogate ERMs (same recording date)
erm_df = pd.read_csv(outdir / "erm-surrogates.csv", index_col=False)
erm_map = {need: have for _, (date, need, have) in erm_df.iterrows()}

# bad/corrupt files
with open(outdir.parent / "bad-files.yaml", "r") as fid:
    bad_files = yaml.load(fid, Loader=yaml.SafeLoader)

# tasks
tasks = dict(
    am="AmplitudeModulatedTones",
    ids="InfantDirectedSpeech",
    mmn="SyllableMismatchNegativity",
)

# event mappings
event_mappings = dict(
    am=dict(),
    ids=dict(),
    mmn=dict(),
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
    if len(erm_files):
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
        # ↓↓↓↓↓↓ TODO TEMPORARY
        # if "mmn" not in raw_file.name:
        #     continue
        # ↑↑↑↑↑↑ TODO TEMPORARY
        for task_code, task_name in tasks.items():
            if task_code in raw_file.name:
                # load the data, then re-write it in the BIDS folder tree
                raw = mne.io.read_raw_fif(raw_file, **read_raw_kw)
                events, _, orig_events = extract_expyfun_events(raw_file)
                # these offsets disambiguate the 3 different experiments
                # we subtract 1 because `extract_expyfun_events` automatically adds one
                # to avoid zero-valued events, but since we're adding additional offsets
                # that's not needed (and is confusing).
                events[:, -1] += event_offsets[task_code] - 1
                parsed_events = score(events, subj, task_code, raw.info["meas_date"])
                bids_path.update(task=task_name)
                write_raw_bids(
                    raw=raw,
                    # events=parsed_events,
                    # event_id=event_mappings[task_code],
                    bids_path=bids_path,
                    empty_room=erm,
                    overwrite=True,
                )

print_dir_tree(bids_root)
