from pathlib import Path

bids_root = Path("/storage/badbaby-redux/bids-data")
fpaths = bids_root.rglob("**/sub-*_ses-?_task-SyllableMismatchNegativity_events.tsv")

for fpath in fpaths:
    text = fpath.read_text()
    for bw in "bw":
        text = text.replace(f"deviant_{bw}a", f"deviant/{bw}a")
    fpath.write_text(text)
