import re
import yaml
from pathlib import Path

import mne
import numpy as np


ecgpath = Path("../ecg-mags.yaml").resolve()
with open(ecgpath) as fid:
    ecgs = yaml.safe_load(fid)

indir = Path(".").resolve()
infiles = indir.glob("*.fif")

pattern = r"(?P<sub>sub-\d{3})_(?P<ses>ses-[abc])_task-AmplitudeModulatedTones_proc-filt_raw.fif"

for infile in infiles:
    res = re.match(pattern, infile.name)
    sub, ses = res.groups()
    # skip ones we've already done
    if ecgs[sub][ses] is not None:
        continue
    # load the raw and plot MAGs
    raw = mne.io.read_raw_fif(infile, verbose=False)
    raw.info["bads"] = []
    fig = raw.plot(picks="mag", block=True)
    # use the one marked as bad as the ECG channel
    mag = np.array(raw.info["bads"]).item()
    ecgs[sub][ses] = mag
    print(f"assigning {mag} to {sub} {ses}")

# log progress
done = 0
total = 0
for sub, sess in ecgs.items():
    for ses, mag in sess.items():
        total += 1
        done += 0 if mag is None else 1
print(f"{done} / {total} done")

with open(ecgpath, "w") as fid:
    yaml.safe_dump(ecgs, fid, default_flow_style=False)

"""
REALLY BAD ONES
116a
116b
122a
122b
124a
133a
134a
218a
228a
301b
312b so/so
"""
