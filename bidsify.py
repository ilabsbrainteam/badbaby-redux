"""Create BIDS folder structure for "badbaby" data."""

from collections import defaultdict
from datetime import date
from pathlib import Path

import mne

from mne_bids import (
    BIDSPath,
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


# path stuff
root = Path().resolve()
orig_data = root / "orig_data"
bids_root = root / "data"

bids_path = BIDSPath(root=bids_root, datatype="meg", suffix="meg", extension=".fif")

# tasks
tasks = dict(
    am="AmplitudeModulatedTones",
    ids="InfantDirectedSpeech",
    mmn="SyllableMismatchNegativity",
)

# container for ERMs. Not all subfolders have an ERM, so this lets us pick a fallback
# ERM recording that occurred on the same day when one is missing for a given subject.
erms = defaultdict(list)
# first loop: find ERM files
# TODO: may not need this first loop (and associated code later) if we work from the
# previous local copy of the data (which had already identified missing/surrogate ERMs)
for data_folder in orig_data.rglob("bad_*/*/"):
    # extract date code from the sub-folder name
    ymd = _get_date_from_dir_path(data_folder)
    # find the empty room files
    erm_files = list(data_folder.glob("*_erm_raw.fif"))
    if len(erm_files):
        erms[ymd.isoformat()].append(erm_files)

# second loop: classify raw files by "task" from the filenames
for data_folder in orig_data.rglob("bad_*/*/"):
    # extract the subject ID
    subj = data_folder.parts[-2].lstrip("bad_")
    if subj.endswith("a"):
        session = "TwoMonth"
    elif subj.endswith("b"):
        session = "SixMonth"
    else:
        raise NotImplementedError(
            "TODO: create lookup table for subjs with no 'a' or 'b' in their subject ID"
        )
    subj = int(subj[:3])

    # find the relevant ERM file. Check current directory first:
    erm_files = list(data_folder.glob("*_erm_raw.fif"))
    if len(erm_files):
        assert len(erm_files) == 1  # there shouldn't ever be 2 ERMs for the same run
        erm = erm_files[0]
    else:
        key = _get_date_from_dir_path(data_folder).isoformat()
        try:
            erm = erm_files[key][0]
            # TODO ↑↑↑ if multiple from that day, ideally would pick one closest in
            # time. That would probably require reading the info from the raw and the
            # ERMs to compare acquisition timestamps.
        except KeyError as err:
            raise RuntimeError(
                f"No ERM file found on {key} for subject {subj}"
            ) from err

    # classify the raw files by task, and write them to the BIDS folder
    for raw_file in data_folder.iterdir():
        for task_code, task_name in tasks.items():
            if task_code in raw_file.name:
                # load the data, then re-write it in the BIDS folder tree
                raw = mne.io.read_raw_fif(raw_file, allow_maxshield=True, preload=False)
                bids_path.update(task=task_name, session=session)
                write_raw_bids(
                    raw=raw,
                    bids_path=bids_path,
                    subject=subj,
                    empty_room=erm,
                )
