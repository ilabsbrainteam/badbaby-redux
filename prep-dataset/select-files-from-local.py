from pathlib import Path
import yaml

root = Path("/storage/badbaby-redux").resolve()
indir = root / "local-data"
outdir = root / "data"

# create initial source → target mapping
infiles = indir.rglob("*.fif")
mapping = {source: outdir / source.relative_to(indir) for source in infiles}

# SKIP REDUNDANT FILES
redundant_files = (
    # DUPLICATE. there are 2 ERMs in bad_209b folder, the files are identical, one has
    # wrong subj name (208b), folder for 208b already has an ERM of different file size.
    indir / "bad_209b" / "raw_fif" / "bad_208b_erm_raw.fif",
    # CORRUPT. larger file with same name in server's `111111` folder.
    indir / "bad_316b" / "raw_fif" / "bad_316b_am_raw.fif",
)
for _file in redundant_files:
    _ = mapping.pop(_file)

# FIX BAD FOLDER NAME: bad_208a/151007 → bad_208/raw_fif
#     The datestamp 151007 indicates that this is actually bad_208 (not bad_208a),
#     cf. the existence of: /mnt/brainstudio/bad_baby/bad_208/151007
#                      and  /mnt/brainstudio/bad_baby/bad_208a/151015
#     TODO: note the two recordings are only 8 days apart; double-check whether the
#     earlier date is still within age criterion for "a" sessions; if so, could use it.
#     NOTE: this one must be first! other fixes depend on `mapping` already having this.
mapping.update(
    {
        source: outdir / "bad_208" / "raw_fif" / source.name
        for source in (indir / "bad_208a" / "151007").glob("*.fif")
    }
)

# FIX CORRUPTED FILES: `raw.fif` is corrupted and `raw2.fif` is good
corrupted_files = (
    indir / "bad_128a" / "raw_fif" / "bad_128a_ids_raw.fif",
    indir / "bad_208a" / "151007" / "bad_208_ids_raw.fif",
)
fix_corrupted = {
    bad_source.parent / bad_source.name.replace("raw.fif", "raw2.fif"): mapping.pop(
        bad_source
    )
    for bad_source in corrupted_files
}
mapping.update(fix_corrupted)

# FIX BAD FILENAME PATTERN: *_erm.fif → *_erm_raw.fif
mapping.update(
    {
        source: mapping[source].parent / source.name.replace("erm.fif", "erm_raw.fif")
        for source in indir.rglob("*_erm.fif")
    }
)

# FIX INDIVIDUAL BAD FILENAME
mapping.update(
    {
        # 208a → 208b. (match containing folder) Typo is more likely than storing a
        # file from run "a" in the folder from run "b", since folder for run "b"
        # wouldn't have existed at the time run "a" files were saved.
        indir / "bad_208b" / "raw_fif" / "bad_208a_erm_raw.fif":
        outdir / "bad_208b" / "raw_fif" / "bad_208b_erm_raw.fif",
    }
)

# SKIP PILOT SUBJECTS
pilots = list(
    filter(
        lambda _file: _file.parts[-3][:5] not in ("bad_1", "bad_2", "bad_3"), mapping
    )
)
for _file in pilots:
    _ = mapping.pop(_file)

# VALIDATE
for source, target in mapping.items():
    src = source.relative_to(indir).parts
    trg = target.relative_to(outdir).parts
    assert len(src) == 3
    assert len(trg) == 3
    assert trg[1] == "raw_fif"
    assert trg[2].startswith(trg[0])  # foldername matches filename

# write to file
with open("files-from-local.yaml", "w") as fid:
    yaml.dump({str(source): str(target) for source, target in mapping.items()}, fid)
