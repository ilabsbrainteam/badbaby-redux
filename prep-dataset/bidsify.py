"""Create BIDS folder structure for "badbaby" data."""

from pathlib import Path
from warnings import filterwarnings

import mne
import pandas as pd
import yaml
from mne_bids import (
    BIDSPath,
    # get_anat_landmarks,
    # write_anat,
    write_meg_calibration,
    write_meg_crosstalk,
    write_raw_bids,
)
from score import (
    EVENT_OFFSETS,
    custom_extract_expyfun_events,
    find_matching_tabs,
    parse_mmn_events,
)

from utils import hardlink

verify_events_against_tab_files = True

mne.set_log_level("WARNING")
# suppress messages about IAS / MaxShield
filterwarnings(
    action="ignore",
    message="This file contains raw Internal Active Shielding data",
    category=RuntimeWarning,
    module="mne",
)
# suppress message about bad filename `*raw2.fif`
filterwarnings(
    action="ignore",
    message=r"This filename \(.*\) does not conform to MNE naming conventions",
    category=RuntimeWarning,
    module="mne",
)
# suppress Pandas warning about concat of empty or all-NA DataFrames. The new behavior
# (keeping NAs) is what we want
filterwarnings(
    action="ignore",
    message="The behavior of DataFrame concatenation with empty or all-NA entries is",
    category=FutureWarning,
)
# escalate SciPy warning so we can catch and handle it
filterwarnings(
    action="error",
    message="invalid value encountered in scalar divide",
    category=RuntimeWarning,
    module="scipy",
)
# escalate MNE-BIDS warning (we don't want to miss these)
filterwarnings(
    action="error",
    message="No events found or provided",
    category=RuntimeWarning,
    module="mne_bids",
)

TEMP_RESTRICTED_SUBJS = ("116", "215")

# path stuff
root = Path("/storage/badbaby-redux").resolve()
orig_data = root / "data"
bids_root = root / "bids-data"
cal_dir = root / "calibration"
mri_dir = root / "anat"
outdir = root / "prep-dataset" / "qc"

with open(root / "metadata" / "daysback.yaml", "r") as fid:
    DAYSBACK = yaml.safe_load(fid)

bids_path = BIDSPath(root=bids_root, datatype="meg", suffix="meg", extension=".fif")

# init logging (erase old log files)
erm_log = outdir / "log-of-ERM-issues-BIDS.txt"
score_log = outdir / "log-of-scoring-issues.txt"
logs = (erm_log, score_log) if verify_events_against_tab_files else (erm_log,)
for log in logs:
    with open(log, "w") as fid:
        pass

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
generic_events = dict(BAD_ACQ_SKIP=999)
event_mappings = dict(
    am=dict(amtone=102),
    ids=dict(trial_0=200, trial_1=201, trial_2=202, trial_3=203, trial_4=204),
    mmn=dict(standard=302, deviant_ba=303, deviant_wa=304),
)

read_raw_kw = dict(allow_maxshield=True, preload=False)

df = None

# we write MRI data once per subj, but we need a raw file loaded in order to properly
# write the `trans` information. Use a signal variable to avoid writing more than once.
last_anat_written = None

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
    # TODO TEMPORARY
    if subj not in TEMP_RESTRICTED_SUBJS:
        continue
    # END TODO
    bids_path.update(subject=subj, session=session)

    # find the ERM file
    erm_files = list(data_folder.glob("*_erm_raw.fif"))
    this_erm_file = None
    erm = None
    # none found
    if not len(erm_files):
        with open(erm_log, "a") as fid:
            fid.write(f"No ERM file found for subject {subj}\n")
    # if more than one ERM found, use default ERM filename until we know the `task_code`
    elif len(erm_files) > 1:
        this_erm_file = erm_files[0].with_name(f"{full_subj}_erm_raw.fif")
        assert this_erm_file in erm_files, erm_files
    # only one ERM for all exps (i.e. the typical case; all run on one day)
    else:
        this_erm_file = erm_files[0]
        if this_erm_file.name in bad_files:
            with open(erm_log, "a") as fid:
                fid.write(
                    f"ERM file found for subject {subj}, but the file is corrupted\n"
                )

    # classify the raw files by task, and write them to the BIDS folder
    for raw_file in data_folder.iterdir():
        if raw_file.name in bad_files:
            continue
        if "_erm_" in raw_file.name:
            continue
        # in case someone was manually trying things out:
        if "_tsss" in raw_file.name or "_pos" in raw_file.name:
            continue
        # loop over experimental tasks
        for task_code, task_name in tasks.items():
            if task_code not in raw_file.name:
                continue
            # load the (possibly experiment-specific) ERM
            if this_erm_file is not None:
                specific_erm = list(filter(lambda f: task_code in f.name, erm_files))
                assert len(specific_erm) in (0, 1)
                if len(specific_erm):
                    this_erm_file = specific_erm[0]
                erm = mne.io.read_raw_fif(this_erm_file, **read_raw_kw)
            else:
                with open(erm_log, "a") as fid:
                    fid.write(
                        f"Something went wrong finding ERM file for subject {subj}\n"
                    )
            # load the data
            raw = mne.io.read_raw_fif(raw_file, **read_raw_kw)
            # check for ERM / data file meas_date match
            raw_meas_date = raw.info["meas_date"]
            if erm is not None:
                erm_meas_date = erm.info["meas_date"]
                if erm_meas_date.date() != raw_meas_date.date():
                    with open(erm_log, "a") as fid:
                        msg = (
                            f"meas_date mismatch between "
                            f"{this_erm_file.name} ({erm_meas_date.date()})"
                            f" and {raw_file.name} ({raw_meas_date.date()})\n"
                        )
                        fid.write(msg)
            # parse the events from the STIM channels
            score_func = (
                parse_mmn_events
                if task_code == "mmn"
                else custom_extract_expyfun_events
            )
            events, orig_events = score_func(raw_file, offset=EVENT_OFFSETS[task_code])
            if verify_events_against_tab_files:
                this_df = find_matching_tabs(
                    events, subj, session, task_code, raw_meas_date, logfile=score_log
                )
                if df is None:
                    df = this_df
                else:
                    df = pd.concat((df, this_df), axis="index", ignore_index=True)
            # write the raw data in the BIDS folder tree
            bids_path.update(task=task_name)
            assert erm is not None, bids_path
            write_raw_bids(
                raw=raw,
                events=events,
                event_id=event_mappings[task_code] | generic_events,
                bids_path=bids_path,
                empty_room=erm,
                anonymize=dict(daysback=DAYSBACK),
                overwrite=True,
            )
            # write the (surrogate) MRI in the BIDS derivatives tree
            if last_anat_written != (subj, session):
                # trans = mne.read_trans(mri_dir / full_subj / f"{full_subj}_trans.fif")
                t1_fname = mri_dir / full_subj / "mri" / "T1.mgz"
                anat_path = (
                    bids_root
                    / "derivatives"
                    / "freesurfer"
                    / "subjects"
                    / f"sub-{subj}"
                    / f"ses-{session}"
                )
                # handle cases where one task was done on a different day
                if len(full_subj.split("_")) > 2:
                    anat_path = anat_path.with_name(f"ses-{session}_task-{task_code}")
                for dirpath, dirnames, filenames in (mri_dir / full_subj).walk():
                    for dirname in dirnames:
                        (anat_path / dirname).mkdir(parents=True, exist_ok=True)
                    for fname in filenames:
                        target = (
                            anat_path / dirpath.relative_to(mri_dir / full_subj) / fname
                        )
                        if fname.endswith("_trans.fif"):
                            target = target.with_name(
                                f"sub-{subj}_{anat_path.name}_trans.fif"
                            )
                        hardlink(source=dirpath / fname, target=target, dry_run=False)
                last_anat_written = (subj, session)
            # write the fine-cal and crosstalk files (once per subject/session)
            cal_path = BIDSPath(root=bids_root, subject=subj, session=session)
            write_meg_calibration(cal_dir / "sss_cal.dat", bids_path=cal_path)
            write_meg_crosstalk(cal_dir / "ct_sparse.fif", bids_path=cal_path)
            # print progress message to terminal
            print(
                f"{subj} {session} {task_code: >3} completed ({len(events): >3} events)"
            )

if verify_events_against_tab_files:
    df.to_csv(outdir / "log-of-fif-to-tab-matches.csv")
