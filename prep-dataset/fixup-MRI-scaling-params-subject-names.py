from pathlib import Path
import re

root = Path(
    "/storage/badbaby-redux/bids-data/derivatives/freesurfer/subjects"
).resolve()

cfg_files = root.glob("**/MRI scaling parameters.cfg")

for cfg_file in cfg_files:
    correct_subj = cfg_file.parts[-2]
    orig_subj = f"bad_{''.join(correct_subj.lstrip("sub-").split('_ses-'))}"
    print(f"{orig_subj} → {correct_subj}")
    text = cfg_file.read_text().split("\n")
    line = text[2]
    assert line.startswith("subject_to")
    text[2] = re.sub(orig_subj, correct_subj, line, count=1)
    text = "\n".join(text)
    cfg_file.write_text(text)
