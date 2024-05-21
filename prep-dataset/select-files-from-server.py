from pathlib import Path
import yaml

root = Path("/storage/badbaby-redux").resolve()
indir = root / "server-data"
outdir = root / "data"

# create initial source → target mapping
infiles = indir.rglob("*.fif")
mapping = {
    source: outdir / source.parents[1].relative_to(indir) / "raw_fif" / source.name
    for source in infiles
}

# SKIP REDUNDANT FILES
redundant_files = (
    # DUPLICATE. Wrong subject IDs; correctly-named file exists in corresponding
    # `111111` folder, and has same size.
    indir / "bad_119b" / "160406" / "bad_119_ids_raw.fif",
    indir / "bad_302a" / "151014" / "bad_302_mmn_raw.fif",
    indir / "bad_302a" / "151020" / "bad_302_ids_raw.fif",
    indir / "bad_312b" / "160614" / "bad_213b_ids_raw.fif",
    # DUPLICATE. missing "_mmn" in filename; correctly-named file exists from local, and
    # has same size.
    indir / "bad_129a" / "160129" / "bad_129a_raw.fif",
    # DUPLICATE. bad_208b_erm_raw.fif is inside folder for 209b. Correctly-named file
    # exists from local, and has same size.
    indir / "bad_209b" / "160219" / "bad_208b_erm_raw.fif",
    # DUPLICATE. bad_301/151005/ folder is exact copy of bad_301a/111111/
    indir / "bad_301" / "151005" / "bad_301_am_raw.fif",
    indir / "bad_301" / "151005" / "bad_301_erm_raw.fif",
    indir / "bad_301" / "151005" / "bad_301_ids_raw.fif",
    indir / "bad_301" / "151005" / "bad_301_mmn_raw.fif",
    # CORRUPT. Extra "_bad_" in filename; correctly-named file exists in same directory
    # and is larger.
    indir / "bad_311a" / "160126" / "bad_311a_mmn_bad_raw.fif",
    # CORRUPT. Filenames are fine but files can't be opened; we have usable copies in
    # the corresponding `111111` folder.
    indir / "bad_218a" / "151202" / "bad_218a_am_raw.fif",
    indir / "bad_226b" / "160525" / "bad_226b_am_raw.fif",
    indir / "bad_316b" / "160701" / "bad_316b_am_raw.fif",
)
for _file in redundant_files:
    _ = mapping.pop(_file)

# SKIP REDUNDANT FOLDERS
redundant_folders = (
    # 209a/151006 and 211a/151019: all files have wrong subj ID (209/211), and all files
    # are duplicated (with correct subj ID) in the corresponding `111111` folder.
    indir / "bad_209a" / "151006",
    indir / "bad_211a" / "151019",
    # 222a/232a: same 232a data exists up a level, in its own folder.
    indir / "bad_222a" / "bad_232a",
)
redundant_files = (
    _file for folder in redundant_folders for _file in folder.rglob("*.fif")
)
for _file in redundant_files:
    _ = mapping.pop(_file)

# FIX BAD FILENAME PATTERN: bad_baby_*, bad_bay_*, bad__baby_* → bad_*
for prefix in ("bad_baby_", "bad_bay_", "bad__baby_"):
    mapping.update(
        {
            source:
            mapping[source].parent / mapping[source].name.replace(prefix, "bad_")
            for source in indir.rglob(f"{prefix}*.fif")
        }
    )

# FIX BAD FILENAME PATTERN: *_erm.fif → *_erm_raw.fif
mapping.update(
    {
        source:
        mapping[source].parent / mapping[source].name.replace("erm.fif", "erm_raw.fif")
        for source in indir.rglob("*_erm.fif")
    }
)

# FIX INDIVIDUAL BAD FILENAMES
mapping.update(
    {
        # 117 → 117b. There is no session 117 without the "a" or "b"; other files in
        # that folder correctly include the "b"
        indir / "bad_117b" / "160323" / "bad_117_ids_raw.fif":
        outdir / "bad_117b" / "raw_fif" / "bad_117b_ids_raw.fif",
        # 143a → 134a. There is no subj 143, so this is clearly a transposition typo.
        indir / "bad_134a" / "160415" / "bad_143a_ids_raw.fif":
        outdir / "bad_134a" / "raw_fif" / "bad_134a_ids_raw.fif",
        # 208_a → 208a (it's the only file in that folder)
        indir / "bad_208_a" / "151015" / "bad_208_mmn_raw.fif":
        outdir / "bad_208a" / "raw_fif" / "bad_208a_mmn_raw.fif",
        # 208a → 208b.  Folder for 208a already has an ERM of a different file size;
        # assume this is just a typo.
        indir / "bad_208b" / "160226" / "bad_208a_erm_raw.fif":
        outdir / "bad_208b" / "raw_fif" / "bad_208b_erm_raw.fif",
        # 309b. missing subject ID
        indir / "bad_309b" / "160523" / "bad_ids_raw.fif":
        outdir / "bad_309b" / "raw_fif" / "bad_309b_ids_raw.fif",
        # 310 → 310a. There is no session 310 without the "a" or "b"; other files in
        # that folder correctly include the "a"
        indir / "bad_310a" / "160112" / "bad_310_ids_raw.fif":
        outdir / "bad_310a" / "raw_fif" / "bad_310a_ids_raw.fif",
        # AVOID CLOBBER (raw.fif → raw2.fif). Prevent file from second MEG session from
        # overwriting earlier run, until we know for sure which one we want (TODO).
        indir / "bad_209b" / "160225" / "bad_209b_mmn_raw.fif":
        outdir / "bad_209b" / "raw_fif" / "bad_209b_mmn_raw2.fif",
    }
)

# 233 & 233b → 233a. All files in this folder have wrong subject ID. There is no folder
# for 233 or 233b, either local or server.
mapping.update(
    {
        source: mapping[source].parent
        / source.name.replace("_233_", "_233a_").replace("_233b_", "_233a_")
        for source in (indir / "bad_233a" / "170106").glob("*.fif")
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
with open("files-from-server.yaml", "w") as fid:
    yaml.dump({str(source): str(target) for source, target in mapping.items()}, fid)
