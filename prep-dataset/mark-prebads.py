#!/usr/bin/env python
import re
import socket
import sys
import yaml
from pathlib import Path
from warnings import filterwarnings

import mne

auto_skip = False
if len(sys.argv) > 1:
    assert len(sys.argv) == 4, (
        "expected either 0 or 3 command-line arguments (subj, session, task)"
    )
    auto_skip = True

hostname = socket.gethostname()
if hostname == "agelaius":  # drammock's machine
    rev = reversed  # work backward from end of list
    mne.cuda.init_cuda()
    n_jobs = 8
elif hostname == "bieber":
    rev = list
    n_jobs = 4
else:
    rev = list
    n_jobs = 1
    mne.utils.warn(
        f"unrecognized hostname {hostname}; setting n_jobs=1. Tweak the script if you "
        "don't like that."
    )

root = Path(__file__).parent
prebads_path = root / "prep-dataset" / "prebads.yaml"
raw_files = sorted((root / "bids-data").glob("sub-*/ses-*/meg/*_meg.fif"))

mne.set_log_level("WARNING")
mne.viz.set_browser_backend("qt")
# suppress messages about IAS / MaxShield
filterwarnings(
    action="ignore",
    message="This file contains raw Internal Active Shielding data",
    category=RuntimeWarning,
    module="mne",
)

pattern = (
    r"(?P<sub>sub-\d{3})_"
    r"(?P<ses>ses-[abc])_"
    r"task-(?P<task>AmplitudeModulatedTones|SyllableMismatchNegativity)_meg\.fif"
)

# pre-populate prebads file with `None`
if not prebads_path.exists():
    prebads = dict()
    for infile in raw_files:
        res = re.match(pattern, infile.name)
        if not res:
            continue
        sub, ses, task = res.groups()
        prebads.setdefault(sub, dict())
        prebads[sub].setdefault(ses, dict())
        prebads[sub][ses][task] = None
    with open(prebads_path, "w") as fid:
        yaml.safe_dump(data=prebads, stream=fid)

# load existing (or newly-created) prebads dict
with open(prebads_path) as fid:
    prebads = yaml.safe_load(fid)

counter = 0
for ix, infile in enumerate(rev(raw_files)):
    res = re.match(pattern, infile.name)
    if not res:
        continue
    sub, ses, task = res.groups()
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
    # load the raw
    print("  loading...", end="", flush=True)
    raw = mne.io.read_raw_fif(infile, preload=True, verbose=False, allow_maxshield=True)
    print("  filtering...", end="", flush=True)
    raw.filter(l_freq=None, h_freq=40, n_jobs=n_jobs)
    print("  resampling...")
    raw.resample(150, n_jobs=n_jobs)
    assert raw.info["sfreq"] == 150
    annot_fname = Path("annots") / f"{sub}_{ses}_task-{task}_annot.fif"
    # add any already-created annotations
    if annot_fname.exists():
        ann = mne.read_annotations(annot_fname)
        if raw.annotations:
            ann += raw.annotations
        raw.set_annotations(ann)
    # set channels we've already marked as bad, then plot
    raw.info["bads"].extend(this_prebads or list())
    fig = raw.plot(
        picks="data",
        block=True,
        precompute=False,
        events=None,
        splash=False,
        duration=30,
        n_channels=25,
        show_scalebars=False,
        overview_mode="channels",
        use_opengl=True,
    )
    # save any changes to annotations
    if "BAD_USER" in raw.annotations.description:
        raw.annotations.save(annot_fname, overwrite=True)
    # update our dict of prebads; for clean YAML, cast np._str_ to str, and MNEBadsList to list
    chs = [str(ch) for ch in raw.info["bads"]]
    prebads[sub][ses][task] = list(chs)
    # save changes to disk after every file
    with open(prebads_path, "w") as fid:
        yaml.safe_dump(data=prebads, stream=fid, default_flow_style=False)
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
