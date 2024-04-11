from pathlib import Path
from subprocess import run


def hardlink(source, target, dry_run=True):
    """Create target dirs, then hardlink."""
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["cp", "-ln", "--preserve=all", str(source), str(target)]
    if not dry_run:
        run(cmd)


dry_run = False

indir = Path("server-data").resolve()
outdir = Path("data").resolve()

# create initial hardlink mapping
infiles = indir.rglob("*.fif")
mapping = {
    source: outdir / source.parents[1].relative_to(indir) / "raw_fif" / source.name
    for source in infiles
}

# DELETE REDUNDANT FILES
redundant_files = (
    # has extra "_bad_" in filename; correctly-named file exists in same directory and is larger
    indir / "bad_311a" / "160126" / "bad_311a_mmn_bad_raw.fif",
    # missing "_mmn" in filename; correctly-named file exists from local, and has same size
    indir / "bad_129a" / "160129" / "bad_129a_raw.fif",
    # bad_208b_erm_raw.fif is inside folder for 209b. There's no correctly-named ERM for 209b on server,
    # but there's already an ERM for 209b in the local data, which has identical file size to this one.
    # Therefore, presumed to be a filename typo / duplicate.
    indir / "bad_209b" / "160219" / "bad_208b_erm_raw.fif",
)
for _file in redundant_files:
    _ = mapping.pop(_file)

# DELETE REDUNDANT FOLDER: 232a inside 222a
#     232a data exists up a level, in its own folder.
redundant_folder = (indir / "bad_222a" / "bad_232a").rglob("*.fif")
for _file in redundant_folder:
    _ = mapping.pop(_file)

# MERGE "perhapsduplicate" FOLDER
#     Ignores files with same names as in original folder
#     (files with same names were first confirmed to have identical file sizes)
originals = (indir / "bad_104" / "151009").rglob("*.fif")
original_names = [x.name for x in originals]
maybe_duplicates = (indir / "bad_104" / "151009perhapsduplicate").rglob("*.fif")
for _file in maybe_duplicates:
    if _file.name in original_names:
        _ = mapping.pop(_file)

# FIX BAD FILENAME: bad_baby_* → bad_*
fix_baby = {
    source: mapping[source].parent / source.name.replace("bad_baby_", "bad_")
    for source in indir.rglob("bad_baby_*.fif")
}

# FIX BAD FILE/FOLDER NAME: bad_208_a → bad_208a
#     (it's the only file in that folder)
fix_208_a = {
    indir / "bad_208_a" / "151015" / "bad_208_mmn_raw.fif":
    outdir / "bad_208a" / "raw_fif" / "bad_208a_mmn_raw.fif"
}

# FIX BAD FILENAME: raw.fif → raw2.fif
#     prevent file from second MEG session from clobbering earlier run,
#     until we know for sure which one we want (TODO).
fix_second_visit = {
    indir / "bad_209b" / "160225" / "bad_209b_mmn_raw.fif":
    outdir / "bad_209b" / "raw_fif" / "bad_209b_mmn_raw2.fif"
}

fixes = (fix_baby, fix_208_a, fix_second_visit,)
for fix in fixes:
    if dry_run:
        for _src, _trg in fix.items():
            print(f"{_src.relative_to(indir.parent)} → {_trg.relative_to(outdir.parent)}\n")
    else:
        mapping.update(fix)

for source, target in mapping.items():
    # this shouldn't be necessary due to -n flag in hardlink command,
    # but let's be extra careful:
    if not target.is_file():
        hardlink(source, target, dry_run)
