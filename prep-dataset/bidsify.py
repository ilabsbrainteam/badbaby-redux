"""Create BIDS folder structure for "badbaby" data."""

import argparse
from pathlib import Path
from warnings import filterwarnings

import mne
import pandas as pd
import yaml
from mne_bids import (
    BIDSPath,
    get_anat_landmarks,
    mark_channels,
    write_anat,
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

# allow passing a subject or multiple subjects via command line
parser = argparse.ArgumentParser(
    description="Create BIDS folder structure for badbaby data",
)
parser.add_argument("SUBJECTS", type=str, nargs="+", help="Subject IDs to process")
args = parser.parse_args()
subjects_to_process = set(args.SUBJECTS)
overwrite = bool(subjects_to_process)  # allow overwriting if specific subjects given

# path stuff
root = Path("/storage/badbaby-redux").resolve()
orig_data = root / "data"
bids_root = root / "bids-data"
cal_dir = root / "calibration"
mri_dir = root / "anat"
prep_dir = root / "prep-dataset"
outdir = prep_dir / "qc"
outdir.mkdir(exist_ok=True)

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
with open(prep_dir / "bad-files.yaml", "r") as fid:
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
    mmn={"standard": 302, "deviant/ba": 303, "deviant/wa": 304},
)

read_raw_kw = dict(allow_maxshield="yes", preload=False)

df = None

# load the list of bad channels ("prebads") that were noted during acquisition
with open(prep_dir / "bad-channels.yaml") as fid:
    prebads = yaml.safe_load(fid)

# load the list of bad dev_head_t files with refit options
with open(prep_dir / "refit-options.yml", "r") as fid:
    refit_options = yaml.load(fid, Loader=yaml.SafeLoader)

# we write MRI data once per subj, but we need a raw file loaded in order to properly
# write the `trans` information. Use a signal variable to avoid writing more than once.
last_anat_written = None

# classify raw files by "task" from the filenames
unprocessed = sorted(subjects_to_process)
for data_folder in sorted(orig_data.rglob("bad_*/raw_fif/")):
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
    if subjects_to_process and subj not in subjects_to_process:
        continue
    if subjects_to_process:
        if subj in unprocessed:
            unprocessed.remove(subj)
    bids_path.update(subject=subj, session=session)

    # look for ERM files
    erm_files = list(data_folder.glob("*_erm_raw.fif"))

    # classify the raw files by task, and write them to the BIDS folder
    for raw_file in sorted(data_folder.iterdir()):
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
            # load the data
            raw = mne.io.read_raw_fif(raw_file, **read_raw_kw)
            # check for experiment-specific ERM file
            task_specific_erm = list(filter(lambda f: task_code in f.name, erm_files))
            assert len(task_specific_erm) in (0, 1)
            if task_specific_erm:
                erm_file = task_specific_erm[0]
            # only one ERM for all tasks (i.e. the typical case; all on one day)
            elif erm_files:
                erm_file = erm_files[0].with_name(f"{full_subj}_erm_raw.fif")
                assert erm_file in erm_files, erm_files
            # no ERM file found
            else:
                with open(erm_log, "a") as fid:
                    fid.write(f"No ERM file found for {full_subj} {task_code}\n")
                erm_file = None
                erm = None
            # check for ERM / data file meas_date match
            raw_meas_date = raw.info["meas_date"]
            if erm_file:
                # make sure we're not hit by a bad file
                if erm_file.name in bad_files:
                    with open(erm_log, "a") as fid:
                        fid.write(
                            f"ERM file found for {full_subj} {task_code}, "
                            f"but the file ({erm_file.name}) is corrupted\n"
                        )
                    break
                # load the (possibly experiment-specific) ERM
                erm = mne.io.read_raw_fif(erm_file, **read_raw_kw)
                erm_meas_date = erm.info["meas_date"]
                if erm_meas_date.date() != raw_meas_date.date():
                    with open(erm_log, "a") as fid:
                        msg = (
                            f"meas_date mismatch: {erm_file.name} "
                            f"({erm_meas_date.date()}) vs. {raw_file.name} "
                            f"({raw_meas_date.date()})\n"
                        )
                        fid.write(msg)
                # no data files have EEG, so expunge EEG channels from ERMs to avoid
                # error in `maxwell_filter_prepare_emptyroom` when copying montage
                if "eeg" in erm:
                    n_eeg = len(erm.get_channel_types(picks="eeg"))
                    with open(erm_log, "a") as fid:
                        msg = (
                            f"montage mismatch: dropping {n_eeg} EEG channels from "
                            f"{erm_file.name}\n"
                        )
                        fid.write(msg)
                    picks = list(set(erm.get_channel_types(unique=True)) - set(["eeg"]))
                    erm.pick(picks)
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
            # fix dev_head_t if needed
            refit_option = refit_options.get(raw_file.name, {}).copy()
            if refit_option.pop("refit", False):
                kwargs = dict(locs=False, amplitudes=False, dist_limit=0.01, colinearity_limit=0.01, verbose=True)
                kwargs.update(refit_option)
                mne.chpi.refit_hpi(raw.info, **kwargs)
            # write the raw data in the BIDS folder tree
            bids_path.update(task=task_name)
            write_raw_bids(
                raw=raw,
                events=events,
                event_id=event_mappings[task_code] | generic_events,
                bids_path=bids_path,
                empty_room=erm,
                anonymize=dict(daysback=DAYSBACK),
                overwrite=True,
            )
            # write the (surrogate) MRI in the BIDS derivatives tree. Since we have
            # separate MRIs for different sessions (they're months apart, and these are
            # infants), we need to rename the subject folder (and some of the files) to
            # use a compound "subject" name like `sub-XXX_ses-Y`
            anat_to_write = (subj, session)
            compound_subj_name = f"sub-{subj}_ses-{session}"
            if last_anat_written != anat_to_write:
                anat_path = (
                    bids_root
                    / "derivatives"
                    / "freesurfer"
                    / "subjects"
                    / compound_subj_name
                )
                # handle cases where one task was done on a different day
                if len(full_subj.split("_")) > 2:
                    compound_subj_name = f"{compound_subj_name}_task-{task_code}"
                    anat_path = anat_path.with_name(compound_subj_name)
                    anat_to_write = (*anat_to_write, task_code)
                for dirpath, dirnames, filenames in (mri_dir / full_subj).walk():
                    for dirname in dirnames:
                        # adjust "subject" name when it's the foldername
                        dirname_out = dirname.replace(full_subj, compound_subj_name)
                        (anat_path / dirname_out).mkdir(parents=True, exist_ok=True)
                    for fname in filenames:
                        # adjust "subject" name when it's incorporated into filenames
                        # (e.g. for the trans- and BEM files)
                        fname_out = fname.replace(full_subj, compound_subj_name)
                        target = (
                            anat_path
                            / dirpath.relative_to(mri_dir / full_subj)
                            / fname_out
                        )
                        hardlink(source=dirpath / fname, target=target, dry_run=False)
                # now use MNE-BIDS to (re)write the T1, so we can get the side
                # effect of converting the trans file to a JSON sidecar
                t1_fname = mri_dir / full_subj / "mri" / "T1.mgz"
                trans = mne.read_trans(anat_path / f"{compound_subj_name}_trans.fif")
                landmarks = get_anat_landmarks(
                    image=t1_fname,
                    info=raw.info,
                    trans=trans,
                    fs_subject=compound_subj_name,
                    fs_subjects_dir=anat_path.parent,
                )
                mri_path = BIDSPath(root=bids_root, subject=subj, session=session)
                nii_file = write_anat(
                    image=t1_fname,
                    bids_path=mri_path,
                    landmarks=landmarks,
                    overwrite=overwrite,
                )
                # update our signal variable
                last_anat_written = anat_to_write
            # write the bad channels
            if prebads[compound_subj_name]:
                mark_channels(
                    bids_path=bids_path,
                    ch_names=[f"MEG{ch}" for ch in prebads[compound_subj_name]],
                    status="bad",
                    descriptions="prebad",
                )
            # write the fine-cal and crosstalk files (once per subject/session)
            cal_path = BIDSPath(root=bids_root, subject=subj, session=session)
            write_meg_calibration(cal_dir / "sss_cal.dat", bids_path=cal_path)
            write_meg_crosstalk(cal_dir / "ct_sparse.fif", bids_path=cal_path)
            # print progress message to terminal
            print(
                f"{subj} {session} {task_code: >3} completed ({len(events): >3} events)"
            )
if unprocessed:
    raise RuntimeError(f"Some subjects were not processed: {unprocessed}")

if verify_events_against_tab_files and not subjects_to_process:
    df.to_csv(outdir / "log-of-fif-to-tab-matches.csv")
