import re
from pathlib import Path
from subprocess import run

indir = Path("server-data")
outdir = Path("data")

subj_dirs = sorted(indir.glob("bad*"))

# mapping from bad filenames to good filenames
known_bads = {
    # "bad_233b_am_raw.fif": "bad_233a_am_raw.fif",
    # "bad_233_mmn_raw.fif": "bad_233a_mmn_raw.fif",
    # "bad_233_ids_raw.fif": "bad_233a_ids_raw.fif",
    # "bad_bay_304a_erm_raw.fif": "bad_304a_erm_raw.fif",
    # "bad_ids_raw.fif": "bad_309b_ids_raw.fif",
    # "bad_baby_311a_mmn_raw.fif": "bad_311a_mmn_raw.fif",
    "bad_311a_mmn_bad_raw.fif": "bad_311a_mmn_raw.fif",  # has extra "bad" in fname,
    # "bad_baby_317a_erm_raw.fif": "bad_317a_erm_raw.fif",
}

known_bads = (
    "bad_311a_mmn_bad_raw.fif",  # extra "bad" in fname, non "bad" exists in same dir
)

for _dir in subj_dirs:
    subj_id = _dir.name
    for second_pass in (False, True):
        for _subdir in _dir.iterdir():
            is_backup_subdir = _subdir.name == "111111"
            # first pass: ignore "111111" subdirs
            if is_backup_subdir and not second_pass:
                continue
            # Second pass: only look at "111111" subdirs
            elif second_pass and not is_backup_subdir:
                continue
            for _fname in _subdir.iterdir():
                # skip files we know we don't want
                if _fname.name in known_bads:
                    continue
                # check that the filename matches the folder
                fname_dirname_mismatch = not _fname.name.startswith(subj_id)
                target = outdir / subj_id / "raw_fif" / _fname.name
                if fname_dirname_mismatch:
                    # If target already exists, don't care about source name mismatch
                    if target.is_file():
                        continue

                    _fname_parts = _fname.name.rsplit("_", maxsplit=2)
                    subj_id_in_fname = _fname_parts[0]
                    # don't try to rename the file from the folder, if the subj_id in
                    # the filename is plausibly valid (i.e., from some other subj)
                    if (outdir / subj_id_in_fname).exists():
                        print(f"folder/filename mismatch ({_fname})")
                        continue
                    _fname_parts[0] = subj_id
                    new_fname = "_".join(_fname_parts)
                    print(f"renaming {_fname} to {new_fname}")
                    target = target.parent / new_fname
                    # _fname = _fname.rename(_fname.parent / new_fname)
                if target.is_file():
                    # if source & target are same size: assume identical, nothing to do
                    if _fname.stat().st_size == target.stat().st_size:
                        continue
                    else:
                        # TODO: unclear what action to take here. Manual resolution?
                        print(f"target exists, size mismatch ({_fname.name})")
                else:
                    # target not present, so hardlink the file
                    print("cp", "-l", str(_fname), str(target))
                    # run("mkdir", "-p", str(target.parent))
                    # run("cp", "-l", str(_fname), str(target))
