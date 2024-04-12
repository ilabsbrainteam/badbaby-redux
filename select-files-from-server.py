from pathlib import Path

indir = Path("server-data").resolve()
outdir = Path("data").resolve()

# create initial source → target mapping
infiles = indir.rglob("*.fif")
mapping = {
    source: outdir / source.parents[1].relative_to(indir) / "raw_fif" / source.name
    for source in infiles
}

# SKIP REDUNDANT FILES
redundant_files = (
    # has extra "_bad_" in filename; correctly-named file exists in same directory and is larger
    indir / "bad_311a" / "160126" / "bad_311a_mmn_bad_raw.fif",
    # missing "_mmn" in filename; correctly-named file exists from local, and has same size
    indir / "bad_129a" / "160129" / "bad_129a_raw.fif",
    # bad_208b_erm_raw.fif is inside folder for 209b. There's no correctly-named ERM for 209b on server,
    # but there's already an ERM for 209b in the local data, which has identical file size to this one.
    # Therefore, presumed to be a filename typo / duplicate.
    indir / "bad_209b" / "160219" / "bad_208b_erm_raw.fif",
    # 119b/160406 has an IDS file with wrong subj ID. Same file is in `111111` folder with correct ID,
    # so skip this one
    indir / "bad_119b" / "160406" / "bad_119_ids_raw.fif",
)
for _file in redundant_files:
    _ = mapping.pop(_file)

# SKIP REDUNDANT FOLDER: 232a inside 222a
#     232a data exists up a level, in its own folder.
redundant_folder = (indir / "bad_222a" / "bad_232a").rglob("*.fif")
for _file in redundant_folder:
    _ = mapping.pop(_file)

# SKIP REDUNDANT FOLDER: 209a/151006
#     all files in there have wrong subj ID (209), and all files are
#     duplicated (with correct subj ID) in the `111111` folder, so just ignore this one.
redundant_folder = (indir / "bad_209a" / "151006").rglob("*.fif")
for _file in redundant_folder:
    _ = mapping.pop(_file)

# SKIP REDUNDANT FOLDER: 211a/151019
#     all files in there have wrong subj ID (211), and all files are
#     duplicated (with correct subj ID) in the `111111` folder, so just ignore this one.
redundant_folder = (indir / "bad_211a" / "151019").rglob("*.fif")
for _file in redundant_folder:
    _ = mapping.pop(_file)

# SKIP "perhapsduplicate" FOLDER
#     Ignores files with same names as in original folder
#     (files with same names were first confirmed to have identical file sizes)
originals = (indir / "bad_104" / "151009").rglob("*.fif")
original_names = [x.name for x in originals]
maybe_duplicates = (indir / "bad_104" / "151009perhapsduplicate").rglob("*.fif")
for _file in maybe_duplicates:
    if _file.name in original_names:
        _ = mapping.pop(_file)

# SKIP CORRUPT FILES
#     for these we have usable copies of the files in the corresponding
#     `111111` folder.
known_corrupt = (
    indir / "bad_316b" / "160701" / "bad_316b_am_raw.fif",
    indir / "bad_226b" / "160525" / "bad_226b_am_raw.fif",
    indir / "bad_218a" / "151202" / "bad_218a_am_raw.fif",
)
for _file in known_corrupt:
    _ = mapping.pop(_file)

# SKIP BAD FILENAME: 302 → 302a
#     Server has folders:
#     - bad_302a/111111/ (am, ids, mmn, erm) labeled as 302a
#     - bad_302a/151014/ (mmn) labeled as 302
#     - bad_302a/151020/ (ids) labeled as 302
#     The "302" files are identical size to corresponding files in
#     the 111111 folder, presumed duplicate, so skip.
wrong_subj = (
    indir / "bad_302a" / "151014" / "bad_302_mmn_raw.fif",
    indir / "bad_302a" / "151020" / "bad_302_ids_raw.fif",
)
for _file in wrong_subj:
    _ = mapping.pop(_file)

# FIX BAD FILENAMES: bad_baby_*, bad_bay_*, bad__baby_* → bad_*
fix_prefix = dict()
for prefix in ("bad_baby_", "bad_bay_", "bad__baby_"):
    fix_prefix.update(
        {
            source: mapping[source].parent / source.name.replace(prefix, "bad_")
            for source in indir.rglob(f"{prefix}*.fif")
         }
    )

# FIX BAD FILENAME: 117 → 117b
#     Note that there is no session 117 without the "a" or "b",
#     and other files in that folder correctly include the "b"
fix_117b = {
    indir / "bad_117b" / "160323" / "bad_117_ids_raw.fif":
    outdir / "bad_117b" / "raw_fif" / "bad_117b_ids_raw.fif"
}

# FIX BAD FILENAME: 143a → 134a
#     Note that there is no subj 143, so this is clearly a transposition typo.
fix_134a = {
    indir / "bad_134a" / "160415" / "bad_143a_ids_raw.fif":
    outdir / "bad_134a" / "raw_fif" / "bad_134a_ids_raw.fif"
}

# FIX BAD FILE/FOLDER NAME: bad_208_a → bad_208a
#     (it's the only file in that folder)
fix_208_a = {
    indir / "bad_208_a" / "151015" / "bad_208_mmn_raw.fif":
    outdir / "bad_208a" / "raw_fif" / "bad_208a_mmn_raw.fif"
}

# FIX BAD FILENAME: 208a → 208b
#     Folder for 208a already has an ERM of a different file size,
#     so assume this is just a typo.
fix_208b = {
    indir / "bad_208b" / "160226" / "bad_208a_erm_raw.fif":
    outdir / "bad_208b" / "raw_fif" / "bad_208b_erm_raw.fif"
}

# FIX FOLDER OF BAD FILENAMES: 233a
#     all files in this folder have wrong subject ID.
#     there is no folder for 233 or 233b, either local or server.
fix_233a = {
    source: mapping[source].parent / source.name.replace("_233_", "_233a_").replace("_233b_", "_233a_")
    for source in (indir / "bad_233a" / "170106").glob("*.fif")
}

# FIX BAD FILENAME: missing subject ID
fix_309b = {
    indir / "bad_309b" / "160523" / "bad_ids_raw.fif":
    outdir / "bad_309b" / "raw_fif" / "bad_309b_ids_raw.fif"
}

# FIX BAD FILENAME: 310 → 310a
#     Note that there is no session 310 without the "a" or "b",
#     and other files in that folder correctly include the "a"
fix_310a = {
    indir / "bad_310a" / "160112" / "bad_310_ids_raw.fif":
    outdir / "bad_310a" / "raw_fif" / "bad_310a_ids_raw.fif"
}

# FIX BAD FILENAME: 213b → 312b
#     Other files in that folder correctly say "312b", and
#     file size matches correctly-named file in the `111111` folder.
fix_312b = {
    indir / "bad_312b" / "160614" / "bad_213b_ids_raw.fif":
    outdir / "bad_312b" / "raw_fif" / "bad_312b_ids_raw.fif"
}

# FIX BAD FILENAME: raw.fif → raw2.fif
#     prevent file from second MEG session from clobbering earlier run,
#     until we know for sure which one we want (TODO).
fix_second_visit = {
    indir / "bad_209b" / "160225" / "bad_209b_mmn_raw.fif":
    outdir / "bad_209b" / "raw_fif" / "bad_209b_mmn_raw2.fif"
}

# SKIP PILOT SUBJECTS
pilots = list(filter(
    lambda _file: _file.parts[-3][:5] not in ("bad_1", "bad_2", "bad_3"),
    mapping
))
for _file in pilots:
    _ = mapping.pop(_file)

# APPLY FIXES
fixes = (fix_prefix, fix_117b, fix_134a, fix_208_a, fix_208b, fix_233a, fix_309b, fix_310a, fix_312b, fix_second_visit,)
for fix in fixes:
    mapping.update(fix)

# SEPARATE OUT THE FAKE-DATED FILES, TO USE ONLY AS FALLBACKS
preferred_mapping = dict()
backup_mapping = dict()
for source, target in mapping.items():
    src = source.relative_to(indir).parts
    trg = target.relative_to(outdir).parts
    assert len(src) == 3
    assert len(trg) == 3
    # assert trg[0] == src[0], (source, target)
    assert trg[1] == "raw_fif"
    assert trg[2].startswith(trg[0])  # foldername matches filename
    if src[1] == "111111":
        backup_mapping[source] = target
    else:
        preferred_mapping[source] = target
