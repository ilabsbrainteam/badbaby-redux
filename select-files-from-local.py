from pathlib import Path
from subprocess import run


def hardlink(source, target, dry_run=True):
    """Create target dirs, then hardlink."""
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["cp", "-ln", "--preserve=all", str(source), str(target)]
    if not dry_run:
        run(cmd)


dry_run = False

indir = Path("local-data").resolve()
outdir = Path("data").resolve()

# first link all prebad.txt files
prebads = indir.rglob("bad_*_prebad.txt")
for source in prebads:
    target = outdir / source.relative_to(indir)
    hardlink(source, target, dry_run)

# now handle FIF files
infiles = indir.rglob("*.fif")
mapping = {
    source: outdir / source.relative_to(indir) for source in infiles
}

# FIX BAD FOLDER NAME: bad_208a/151007 → bad_208/raw_fif
#     The datestamp 151007 indicates that this is actually bad_208 (not bad_208a),
#     cf. the existence of: /mnt/brainstudio/bad_baby/bad_208/151007
#                      and  /mnt/brainstudio/bad_baby/bad_208a/151015
#     TODO: note the two recordings are only 8 days apart; double-check whether the
#     earlier date is still within age criterion for "a" sessions; if so, could use it.
fix_208a_208 = {
    source: outdir / "bad_208" / "raw_fif" / source.name
    for source in (indir / "bad_208a" / "151007").glob("*.fif")
}
# this one must be updated right away! other fixes depend on `mapping` already having this.
mapping.update(fix_208a_208)

# FIX BAD FILENAME: 208a → 208b, to match containing folder
#     Assumption here is that a typo is more likely than storing a file from run "a" in
#     the folder from run "b", since a folder for run "b" wouldn't have existed at the
#     time run "a" files were saved.
source = indir / "bad_208b" / "raw_fif" / "bad_208a_erm_raw.fif"
fix_208a_208b = {
    source: outdir / source.parent.relative_to(indir) / source.name.replace("208a", "208b")
}

# FIX BAD FILENAMES: *_erm.fif → *_erm_raw.fif
fix_erm = {
    source: mapping[source].parent / source.name.replace("erm.fif", "erm_raw.fif")
    for source in indir.rglob("*_erm.fif")
}

# FIX CORRUPTED FILES: these two we know that `raw.fif` is corrupted and `raw2.fif` is good
corrupted_files = (
    indir / "bad_128a" / "raw_fif" / "bad_128a_ids_raw.fif",
    indir / "bad_208a" / "151007" / "bad_208_ids_raw.fif",
)
fix_corrupted = {
    bad_source.parent / bad_source.name.replace("raw.fif", "raw2.fif"): mapping.pop(bad_source)
    for bad_source in corrupted_files
}

# REMOVE DUPLICATE: bad_208b_erm_raw.fif
# there are 2 ERMs in bad_209b folder, the files are identical, one has wrong subj name (208b),
# and the folder for 208b already has an ERM of different file size. Thus delete the duplicate.
key = indir / "bad_209b" / "raw_fif" / "bad_208b_erm_raw.fif"
_ = mapping.pop(key)

fixes = (fix_208a_208b, fix_erm, fix_corrupted)
for fix in fixes:
    if dry_run:
        for _src, _trg in fix.items():
            print(f"{_src.relative_to(indir.parent)} → {_trg.relative_to(outdir.parent)}\n")
    else:
        mapping.update(fix)

for source, target in mapping.items():
    hardlink(source, target, dry_run)
