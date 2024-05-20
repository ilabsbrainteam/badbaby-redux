"""Create BIDS folder structure for "badbaby" data."""

from pathlib import Path
from warnings import filterwarnings

import mne
import pandas as pd
import yaml
from mne_bids import (
    BIDSPath,
    print_dir_tree,
    write_meg_calibration,
    write_meg_crosstalk,
    write_raw_bids,
)
from score import (
    EVENT_OFFSETS,
    custom_extract_expyfun_events,
    find_matching_tabs,
    parse_mmn_events,
    score,
)

# suppress messages about IAS / MaxShield
mne.set_log_level("WARNING")
filterwarnings(
    action="ignore",
    message="This file contains raw Internal Active Shielding data",
    category=RuntimeWarning,
    module="mne",
)
# suppress Pandas warning about concat of empty or all-NA DataFrames
filterwarnings(
    action="ignore",
    message="The behavior of DataFrame concatenation with empty or all-NA entries is",
    category=FutureWarning,
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

df = None

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
    # TODO TEMP COMMENT OUT
    # write_meg_calibration(cal_dir / "sss_cal.dat", bids_path=bids_path)
    # write_meg_crosstalk(cal_dir / "ct_sparse.fif", bids_path=bids_path)

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
        # TODO TEMP COMMENT OUT
        # erm = mne.io.read_raw_fif(this_erm_file, **read_raw_kw)
        erm = None  # TODO TEMP

    # classify the raw files by task, and write them to the BIDS folder
    for raw_file in data_folder.iterdir():
        if raw_file.name in bad_files:
            continue
        for task_code, task_name in tasks.items():
            if task_code in raw_file.name:
                # load the data, then re-write it in the BIDS folder tree
                # raw = mne.io.read_raw_fif(raw_file, **read_raw_kw)  # TODO TEMP
                info = mne.io.read_info(raw_file)  # TODO TEMP
                parse_func = (
                    parse_mmn_events
                    if task_code == "mmn"
                    else custom_extract_expyfun_events
                )
                # the offsets disambiguate the 3 different experiments. Not strictly
                # necessary, but helpful.
                events, orig_events = parse_func(
                    raw_file, offset=EVENT_OFFSETS[task_code]
                )
                this_df = find_matching_tabs(
                    events,
                    subj,
                    session,
                    task_code,
                    info["meas_date"],  # raw.info["meas_date"]
                    logfile=score_log,
                )
                if df is None:
                    df = this_df
                else:
                    df = pd.concat((df, this_df), axis="index", ignore_index=True)
                for _fname in this_df["tab_fname"]:
                    print(f"{subj} {task_code: >3}: {_fname}")
                if len(this_df) > 1:
                    raise RuntimeError
                # print(f"parsed {events.shape[0]} events for {raw_file.name} {msg}")
                # continue
                # bids_path.update(task=task_name)
                # write_raw_bids(
                #     raw=raw,
                #     # events=parsed_events,
                #     # event_id=event_mappings[task_code],
                #     bids_path=bids_path,
                #     empty_room=erm,
                #     overwrite=True,
                # )

df.to_csv(outdir / "log-of-fif-to-tab-matches.csv")
print(df)
# print_dir_tree(bids_root)
