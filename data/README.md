# About the data source

General folder structure is: `bad_{SUBJ_NUM} / {6_DIGIT_DATE_CODE} / {SEVERAL_RAW_FIFF_FILES}`.
Expected Raw FIFF files in each data folder are:

- `*_am_raw.fif` (amplitude modulated tone stimulus)
- `*_ids_raw.fif` (infant-directed speech stimulus)
- `*_mmn_raw.fif` (syllable-based mismatch negativity stimulus)
- `*_erm_raw.fif` (empty room recording)
- some derivative `*_ave.fif` files, which we ignore here

See below for exceptions and how they were handled.

## Inconsistencies

There are some inconsistent file names / paths in the dataset:

- `/mnt/brainstudio/bad_baby/` is the main data folder. It contains:
    - 142 folders matching the regex `r"bad_\d{3}[ab]?"`. Those folders are all that was
      copied to the analysis computer (and from within them, only `*_raw.fif` files were
      copied).
    - ~~3 pilot folders (2 of the form `{SURNAME}_{FIRSTNAME}` of institute staff, and
      one `pilot_6_month`)~~ **IGNORED**.
    - ~~1 `.DS_Store` file~~ **IGNORED**.
    - 1 folder `bad_baby` that looks like a partial copy of the dataset (59 subject
      folders), probably a backup error (e.g. a missing trailing slash in an rsync
      call): **TODO NEEDS FOLLOW-UP**. Within this (possibly to-be ignored) directory:
        - subject folders `bad_120a/`, `bad_129b/`, `bad_213/`, `bad_232b/` are each missing the date-stamp subfolder
        - `bad_226a/` has inside it another subject folder tree `bad_225a/160115/`.
        - filename of `bad_317a/160331/bad_baby_317a_erm_raw.fif` begins "bad_baby_" instead of "bad_"

- Within the subject folders copied to the analysis computer, there are the following
  irregularities:
    - *Lots* of the subjects have a 6-digit date code of `111111` for the subfolder name.
      Surely that is a sigil and not an actual date, as other dates are all in
      2015-2017, and the sheer number of subjects with the `111111` "date" would have
      been impossible to run all in one day. **TODO NEEDS FOLLOW-UP.**
    - `bad_104/151009perhapsduplicate/` has a suggestive-looking subfolder name.
      **TODO NEEDS FOLLOW-UP.**
    - `bad_222a/` has inside it a data folder `160106` as well as a subject folder tree
      `bad_232a/160404/`. The errant extra subject tree is **IGNORED** because it
      contains a subset of files identical to those found at the correct location
      (`/mnt/brainstudio/bad_baby/bad_232a/160404`). Best guess is that this was a GUI
      drag-drop error, from some time before the data were archived.
    - some filenames in `bad_202/150916/` begin "bad_baby_" instead of "bad_"
    - some filenames in `bad_203/150915/` begin "bad_baby_" instead of "bad_"
    - some filenames in `bad_304a/151103/` begin "bad_bay_" instead of "bad_"
    - some filenames in `bad_309b/160523/` lack the subject number in the filename
    - some filenames in `bad_317a/160331/` begin "bad_baby_" instead of "bad_"
    - some filenames in `bad_911/150625/` have an extra `_1` after the subject number

## Multiple runs

Some subject numbers are 3 digits, e.g. `301`. Others are suffixed with either `a` or `b`.
Within a given subject folder, there may be multiple date-code folders. One of the more
complicated examples is `301`:

- `bad_301/151005/*_raw.fif`
- `bad_301a/111111/*_raw.fif`
- `bad_301b/160216/*_raw.fif`
- `bad_301b/160301/*_raw.fif`

**TODO** we need a policy for which recordings/runs to select or discard.
