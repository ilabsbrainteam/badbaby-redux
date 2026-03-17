# Bad Baby reanalysis

This repo is for reanalysis of the "Bad Baby" data, using the MNE-BIDS-Pipeline.


## Notes on data sources and data munging

- local folder `/media/<REDACTED>/Untitled` contains badbaby data with `prebad` files defined and many missing emptyroom files tracked down. This is our starting point, rsync'd to `./local-data`.

- server folder `/mnt/brainstudio/badbaby/` has lots of anomalies / redundancies. It gets rsync'd to `./server-data`.

- file and folder naming anomalies and known-bad-file exclusions are handled by `prep-dataset/select-files-from-*.py`


## Data prep

There is a `Makefile` in the `prep-dataset` folder. `make all` will:

1. rsync data from local and remote sources.
2. sort through the copied file trees, generate a mapping from filenames we want to keep to new file locations in `./data` (correcting folder- or file-names along the way), and make a hardlink to each "kept" file at the new location.
3. write summaries of how much data we have for each subject/session.
4. generate logs / lists of missing or unexpected files.


## BIDSification and processing

Once all the original data files are in place, we can proceed with a 3-step conversion process. To restart from scratch, you can do:
```console
$ rm -Rf ./anat ./bids-data
```

### 1. Anatomical mapping

The script `prep-dataset/rerun-coreg.py` will load the participant digitization, coregister, and create `./anat` and subdirectories with scaled MRIs for each subject and session.

### 2. Converting to BIDS

The script `prep-dataset/bidsify.py` will convert the dataset in `./data` to BIDS format in `./bids-data`. It also checks/validates the events found in the FIF files against the TAB files from the stimulus presentation script (enabled in the `bidsify.py` script via a boolean flag `verify_events_against_tab_files`). Any failures to match up events from the FIF and TAB files will be flagged in `prep-dataset/qc/log-of-scoring-issues.txt`.

### 3. Running the Pipeline

Files related to the preprocessing pipeline are in `./pipeline`.
It can be invoked using standard `MNE-BIDS-Pipeline` mechanics:

- `mne_bids_pipeline --config=pipeline/config.py` will process all data
- View the pipeline reports at `./bids-data/derivatives/mne-bids-pipeline/sub-XXX/ses-Z/meg/sub-XXX_ses-Y_report.html`
