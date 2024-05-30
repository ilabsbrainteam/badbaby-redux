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

# FIX BAD FILENAME PATTERN: bad_baby_*, bad_bay_*, bad__baby_* → bad_*
for prefix in ("bad_baby_", "bad_bay_", "bad__baby_"):
    # fmt: off
    mapping.update(
        {
            source:
            mapping[source].parent / mapping[source].name.replace(prefix, "bad_")
            for source in indir.rglob(f"{prefix}*.fif")
        }
    )
    # fmt: on

# FIX BAD FILENAME PATTERN: *_erm.fif → *_erm_raw.fif
# fmt: off
mapping.update(
    {
        source:
        mapping[source].parent / mapping[source].name.replace("erm.fif", "erm_raw.fif")
        for source in indir.rglob("*_erm.fif")
    }
)
# fmt: on

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
    # BAD DATA. First session note: "cap shifted, reschedule". Have second session file.
    indir / "bad_209b" / "160219" / "bad_209b_mmn_raw.fif",
    # DUPLICATE. subj has 2 session folders, 1st only contains ERM (2nd has ERM too)
    indir / "bad_102" / "150917" / "bad_102_erm.fif",
    # DUPLICATE. bad_301/151005/ folder is exact copy of bad_301a/111111/
    indir / "bad_301" / "151005" / "bad_301_am_raw.fif",
    indir / "bad_301" / "151005" / "bad_301_erm_raw.fif",
    indir / "bad_301" / "151005" / "bad_301_ids_raw.fif",
    indir / "bad_301" / "151005" / "bad_301_mmn_raw.fif",
    # SUPERSEDED. appt log: bad_301b/160216 MMN redone at later date (we have that file)
    indir / "bad_301b" / "160216" / "bad_301b_mmn_raw.fif",
    # CORRUPT. Extra "_bad_" in filename; correctly-named file exists in same directory
    # and is larger.
    indir / "bad_311a" / "160126" / "bad_311a_mmn_bad_raw.fif",
    # CORRUPT. file cannot be opened ("no raw data in file").
    indir / "bad_317a" / "160331" / "bad_baby_317a_erm_raw.fif",
    # CORRUPT. Filenames are fine but files can't be opened; we have usable copies in
    # the corresponding `111111` folder.
    indir / "bad_218a" / "151202" / "bad_218a_am_raw.fif",
    indir / "bad_218a" / "151202" / "bad_218a_am_raw2.fif",
    indir / "bad_226b" / "160525" / "bad_226b_am_raw.fif",
    indir / "bad_316b" / "160701" / "bad_316b_am_raw.fif",
    # CORRUPT. file can be opened, but has wrong event triggers due to wrong cabling.
    indir / "bad_305a" / "151105" / "bad_305a_mmn_raw.fif",
    indir / "bad_108" / "151106" / "bad_108_am_raw.fif",
    indir / "bad_108" / "151106" / "bad_108_erm_raw.fif",
    indir / "bad_108" / "151106" / "bad_108_ids_raw.fif",
    indir / "bad_108" / "151106" / "bad_108_mmn_raw.fif",
    indir / "bad_212" / "151104" / "bad_212_am_raw.fif",
    indir / "bad_212" / "151104" / "bad_212_ids_raw.fif",
    indir / "bad_212" / "151104" / "bad_212_mmn_raw.fif",
    indir / "bad_212" / "111111" / "bad_212_am_raw.fif",
    indir / "bad_212" / "111111" / "bad_212_ids_raw.fif",
    indir / "bad_212" / "111111" / "bad_212_mmn_raw.fif",
    # DUPLICATE. not sure where extra ERM file came from, but `local` has one already
    indir / "bad_131b" / "111111" / "bad_131b_erm_raw.fif",
    indir / "bad_231b" / "111111" / "bad_231b_erm_raw.fif",
    # EXTRANEOUS. second ERM from same day (exclude the early-morning one in favor of
    # the one collected just after subj run)
    indir / "bad_316b" / "111111" / "bad_316b_erm_raw.fif",
    # SUPERSEDED. has `raw.fif` and `raw2.fif`; correct one taken from local files.
    indir / "bad_128a" / "160126" / "bad_128a_ids_raw2.fif",
    indir / "bad_128a" / "160126" / "bad_128a_ids_raw.fif",
    indir / "bad_128a" / "111111" / "bad_128a_ids_raw.fif",
    # SUPERSEDED. has `raw.fif` and `raw2.fif`; `raw2.fif` used in separate block below.
    indir / "bad_202" / "150916" / "bad_baby_202_ids_raw.fif",
    indir / "bad_208" / "151007" / "bad_208_ids_raw.fif",
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
    # BAD DATA. Session note: "two 2-month sessions, neither successful"
    indir / "bad_107" / "151013",
    indir / "bad_107" / "151022",
    # BAD TRIGGERS. Session note: "coming back for 2nd session: bad data cable"
    indir / "bad_304a" / "151103",
)
redundant_files = (
    _file for folder in redundant_folders for _file in folder.rglob("*.fif")
)
for _file in redundant_files:
    _ = mapping.pop(_file)

# FIX INDIVIDUAL BAD FILENAMES
# fmt: off
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
        # For this subj we need to keep both ERMs because MMN session was on different
        # day than other sessions
        indir / "bad_301b" / "160301" / "bad_301b_erm_raw.fif":
        outdir / "bad_301b" / "raw_fif" / "bad_301b_erm_raw2.fif",
        # CORRUPTED: `raw.fif` is corrupted and `raw2.fif` is good
        indir / "bad_208" / "151007" / "bad_208_ids_raw2.fif":
        outdir / "bad_208" / "raw_fif" / "bad_208_ids_raw.fif",
        # keep `*ids_raw2.fif` but remove the `2` (`*ids_raw.fif` removed above)
        indir / "bad_202" / "150916" / "bad_baby_202_ids_raw2.fif":
        outdir / "bad_202" / "raw_fif" / "bad_202_ids_raw.fif",
    }
)
# fmt: on

# COMPLICATED. server folder bad_223b/170508 has implausible date given subj birthdate
# (meas_date in files agree: this was ~18mo not ~6mo). However, meas_date matches
# appointment log date for subj 233b (which doesn't have a folder of data files)
mapping.update(
    {
        source: outdir / "bad_233b" / "raw_fif" / source.name.replace("223", "233")
        for source in (indir / "bad_223b" / "170508").glob("*.fif")
    }
)
# 233 & 233b → 233a. All files in this folder have wrong subject ID (relative to
# containing folder). There is no folder for 233 or 233b (except the one created in the
# immediately preceding statement), either local or server.
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
