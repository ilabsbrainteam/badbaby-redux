import sys
import yaml
from pathlib import Path
from warnings import warn

import pandas as pd

# path stuff
root = Path("/storage/badbaby-redux").resolve()
bids_root = root / "bids-data"

# get list of subjects present in BIDS dataset
SUBJECTS = sorted(
    path.name
    for path in bids_root.glob("sub-???")  # exactly 3 chars, will exclude sub-emptyroom
)
SESSIONS = ["a", "b", "c"]
TASKS = dict(
    am="AmplitudeModulatedTones",
    ids="InfantDirectedSpeech",
    mmn="SyllableMismatchNegativity",
)

task_code = sys.argv[1]
task = TASKS[task_code]

# load the data about which components are bad
INFILE = f"bad-ICA-components-{task_code}.yaml"
with open(Path(__file__).parent / INFILE, "r") as fid:
    ica_bads = yaml.safe_load(fid)

# transfer the bad component info into the BIDS derivative file
for subj in SUBJECTS:
    subj_key = int(subj.replace("sub-", ""))
    for sess in SESSIONS:
        folder = bids_root / subj / f"ses-{sess}"
        # not all subjects have data for all sessions:
        if not folder.exists():
            # if no data for that subj/session, we shouldn't have ICA bads either
            if ica_bads[subj_key].get(sess) is not None:
                raise RuntimeError(
                    f"no BIDS data for {subj} ses-{sess}, but ICA bads found for that "
                    "combo. Something is wrong here."
                )
            continue
        # path to derivative file, where the ICA component marking needs to happen
        deriv_file = (
            bids_root
            / "derivatives"
            / "mne-bids-pipeline"
            / subj
            / f"ses-{sess}"
            / "meg"
            / f"{subj}_ses-{sess}_task-{task}_proc-ica_components.tsv"
        )
        if not deriv_file.exists():
            warn(f"no ICA components file found for {subj} ses-{sess}", RuntimeWarning)
            continue
        df = pd.read_csv(deriv_file, sep="\t", na_filter=False)
        for mapping in ica_bads[subj_key][sess]:
            for reason, bads in mapping.items():
                already_bad = df["status"] == "bad"
                newly_bad = df["component"].isin(bads)
                df.loc[newly_bad & ~already_bad, "status"] = "bad"
                df.loc[newly_bad & ~already_bad, "status_description"] = reason
        df.to_csv(deriv_file, sep="\t", index=False)
