#!/usr/bin/env python
"""Mark bad channels interactively."""

import re
import socket
import sys
import yaml
from pathlib import Path
from warnings import filterwarnings

sys.path.insert(0, str(Path(__file__).parent))
from utils import tasks
sys.path.pop(0)

import mne

tasks_with_erm = dict(tasks)
tasks_with_erm["erm"] = "ERM"
if "ids" in tasks_with_erm:
    del tasks_with_erm["ids"]
del tasks

auto_skip = False
n_channels = 25
if len(sys.argv) > 1:
    assert len(sys.argv) == 4, (
        "expected either 0 or 3 command-line arguments (subj, session, task)"
        f" got {sys.argv[1:]}"
    )
    auto_skip = True

hostname = socket.gethostname()
resample = 80  # equiv to 40 Hz lowpass
if hostname == "agelaius":  # drammock's machine
    rev = reversed  # work backward from end of list
    mne.cuda.init_cuda()
    n_jobs = 8
elif hostname == "bieber":
    rev = list
    n_jobs = 4
elif hostname == "bunk.ilabs.washington.edu":
    rev = list
    n_jobs = 4
    n_channels = 34  # 204 (number of grad channels) is divisible by this
    resample = False  # faster not to (plotting is still fast)
else:
    rev = list
    n_jobs = 1
    mne.utils.warn(
        f"unrecognized hostname {hostname}; setting n_jobs=1. Tweak the script if you "
        "don't like that."
    )

root = Path(__file__).parent.parent
prebads_path = root / "prep-dataset" / "prebads.yaml"
raw_files = sorted((root / "data").glob("bad_*/raw_fif/*_raw.fif"))
assert raw_files

mne.set_log_level("WARNING")
mne.viz.set_browser_backend("qt")
# suppress messages about IAS / MaxShield
filterwarnings(
    action="ignore",
    message="This file contains raw Internal Active Shielding data",
    category=RuntimeWarning,
    module="mne",
)


tasks_or_str = "|".join(tasks_with_erm)
pattern = (
    r"bad_(?P<sub>\d{3})"
    r"(?P<ses>[abc]?)_"
    fr"(?P<task>{tasks_or_str})_raw\.fif"
)


def match(name):
    res = re.match(pattern, name)
    sub, ses, task_key = res.groups()
    task = tasks_with_erm[task_key]
    if not ses:  # can be empty
        ses = "c"
    sub = f"sub-{sub}"
    ses = f"ses-{ses}"
    return sub, ses, task


def files_sort(path):
    sub, ses, task = match(path.name)
    return (sub, ses, list(tasks_with_erm.values()).index(task))


raw_files_filt = sorted(
    (raw_file for raw_file in raw_files if re.match(pattern, raw_file.name)),
    key=files_sort,
)
assert raw_files_filt
raw_files = raw_files_filt
del raw_files_filt


def save_prebads():
    """Save the prebads YAML file."""
    with open(prebads_path, "w") as fid:
        yaml.safe_dump(data=prebads, stream=fid, default_flow_style=False)


# pre-populate prebads file with `None`
if not prebads_path.exists():
    prebads = dict()
    for infile in raw_files:
        sub, ses, task = match(infile.name)
        prebads.setdefault(sub, dict())
        prebads[sub].setdefault(ses, dict())
        prebads[sub][ses][task] = None
    save_prebads()

# load existing (or newly-created) prebads dict
with open(prebads_path) as fid:
    prebads = yaml.safe_load(fid)

# Translate any old values if needed
any_changed = False
for sub, sess in prebads.items():
    for ses, ses_tasks in sess.items():
        for task in list(ses_tasks):
            if task.startswith("AmplitudeModulated"):
                ses_tasks[tasks_with_erm["am"]] = ses_tasks.pop(task)
                any_changed = True
            elif task.startswith("SyllableMismatch"):
                ses_tasks[tasks_with_erm["mmn"]] = ses_tasks.pop(task)
                any_changed = True
        if tasks_with_erm["erm"] not in ses_tasks:
            ses_tasks[tasks_with_erm["erm"]] = None
            any_changed = True
if any_changed:
    save_prebads()

counter = 0
for ix, infile in enumerate(rev(raw_files)):
    sub, ses, task = match(infile.name)
    # skip session C for now to save time
    if ses == "ses-c":
        continue
    # auto-skip if sub,ses,task passed on command line
    if auto_skip:
        if sub != sys.argv[1] or ses != sys.argv[2] or task != sys.argv[3]:
            counter += 1
            continue
        else:
            print(f"Skipped {counter} files, starting with {' '.join(sys.argv[1:])}")
            auto_skip = False
    # option to skip ones already marked / annotated
    this_prebads = prebads[sub][ses][task]
    sub_ses_task = f"{sub} {ses} {task}"
    if this_prebads is not None:
        resp = input(f"{sub_ses_task}: existing bads {this_prebads}. Skip? [y/N] ")
        if len(resp) and resp.lower()[0] == "y":
            continue
    else:
        print(f"{sub_ses_task}: no existing bads")
    # load the raw
    print("  loading...", end="", flush=True)
    raw = mne.io.read_raw_fif(infile, preload=True, verbose=False, allow_maxshield=True)
    if resample:
        print("  resampling...")
        raw.resample(resample, n_jobs=n_jobs)
        assert raw.info["sfreq"] == 80
    annot_fname = Path("annots") / f"{sub}_{ses}_task-{task}_annot.fif"
    # add any already-created annotations
    if annot_fname.exists():
        ann = mne.read_annotations(annot_fname)
        if raw.annotations:
            ann += raw.annotations
        raw.set_annotations(ann)
    # set channels we've already marked as bad, then plot
    raw.info["bads"].extend(this_prebads or list())
    print("  plotting...", end="", flush=True)
    fig = raw.plot(
        picks="data",
        block=True,
        precompute=False,
        events=None,
        splash=False,
        duration=30,
        n_channels=n_channels,
        show_scalebars=False,
        overview_mode="channels",
        lowpass=40 if not resample else None,
        use_opengl=True,
    )
    # save any changes to annotations
    if "BAD_USER" in raw.annotations.description:
        raw.annotations.save(annot_fname, overwrite=True)
    # update our dict of prebads; for clean YAML, cast np._str_ to str, and MNEBadsList to list
    chs = [str(ch) for ch in raw.info["bads"]]
    prebads[sub][ses][task] = list(chs)
    # save changes to disk after every file
    save_prebads()
    # offer chance to quit cleanly
    resp = input(f"{sub_ses_task}: assigned bads {chs}. Continue? [Y/n] ")
    if len(resp) and resp.lower()[0] != "y":
        break

# log overall progress
done = 0
total = 0
for sub, sess in prebads.items():
    for ses, tasks in sess.items():
        for task, data in tasks.items():
            total += 1
            done += 0 if data is None else 1
print(f"{done} / {total} done")
print(
    f"last file touched: '{sub_ses_task}'. Pass that on the command line next time "
    "(and skip it if you're done with it) to resume where you left off."
)
