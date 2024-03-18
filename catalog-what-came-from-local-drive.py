import re
from pathlib import Path

import pandas as pd

expected_files = {
    "prebad.txt": [],
    "mmn_raw.fif": [],
    "am_raw.fif": [],
    "ids_raw.fif": [],
    "erm_raw.fif": [],
}
pattern = f"bad.*({'|'.join(expected_files)})$"

root = Path("local-data").resolve()
subj_dirs = sorted(root.glob("bad*"))

df_index = [x.name.lstrip("bad_") for x in subj_dirs]

for _dir in subj_dirs:
    for _fname in (_dir / "raw_fif").iterdir():
        if not re.match(pattern, _fname.name):
            print(f"unexpected file: {_fname}")
        for _kind in expected_files:
            expected_files[_kind].append(_fname.name.endswith(_kind))

result = pd.DataFrame(data=expected_files, index=df_index)
result.columns = [re.split(r"_|\.", x)[0] for x in result.columns]
result.to_csv("files-from-local-drive.csv")

print(f"Total subjects: {result.shape[0]}")
print(result.sum())
