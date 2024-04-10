from pathlib import Path
from subprocess import run

indir = Path("server-data")
outdir = Path("data")

subj_dirs = sorted(indir.glob("bad*"))

known_bads = (
)
known_corrupt = (
    indir / "bad_316b" / "160701" / "bad_316b_am_raw.fif",
    indir / "bad_226b" / "160525" / "bad_226b_am_raw.fif",
    indir / "bad_218a" / "151202" / "bad_218a_am_raw.fif",
)

dry_run = False

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
                if _fname.name in known_bads or _fname in known_corrupt:
                    continue
                # construct the target (destination to copy to)
                target = outdir / subj_id / "raw_fif" / _fname.name
                # check that the filename matches the folder
                if not _fname.name.startswith(subj_id):
                    # If target already exists, we don't care about source name mismatch
                    if target.is_file():
                        continue
                    # get the subject ID from the filename
                    _fname_parts = _fname.name.rsplit("_", maxsplit=2)
                    subj_id_in_fname = _fname_parts[0]
                    # don't try to rename the file from the folder, if the subj_id in
                    # the filename is plausibly valid (i.e., from some other subj)
                    if (outdir / subj_id_in_fname).exists():
                        print(f"folder/filename mismatch ({_fname})")
                        continue
                    # rewrite filename to have subject ID from the containing folder,
                    # and update the target accordingly
                    _fname_parts[0] = subj_id
                    new_fname = "_".join(_fname_parts)
                    if dry_run:
                        print(f"renaming {_fname} to {new_fname} and updating target")
                    else:
                        _fname = _fname.rename(_fname.parent / new_fname)
                    target = target.parent / new_fname
                # filename/foldername mismatches handled. Check if the target exists:
                if target.is_file():
                    source_size = _fname.stat().st_size
                    target_size = target.stat().st_size
                    # if source & target are same size: assume identical, nothing to do
                    if source_size == target_size:
                        continue
                    else:
                        # TODO: unclear what action to take here. Manual resolution?
                        print(
                            f"target exists, size mismatch ({_fname.name}): "
                            f"local is {target_size}, server is {source_size}")
                else:
                    # target not present, so hardlink the file (`-n` prevents overwrite)
                    if dry_run:
                        print(f"copying  {_fname} to {target}")
                    else:
                        run(["mkdir", "-p", str(target.parent)])
                        run(["cp", "-ln", str(_fname), str(target)])
