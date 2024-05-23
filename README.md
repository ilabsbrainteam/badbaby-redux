# Bad Baby reanalysis

This repo is for reanalysis of the "Bad Baby" data, using the MNE-BIDS-Pipeline.


## Notes on data sources and data munging

- local folder `/media/mdclarke/Untitled` contains badbaby data with `prebad` files defined and many missing emptyroom files tracked down. This is our starting point, rsync'd to `/storage/badbaby-redux/local-data`.

- server folder `/mnt/brainstudio/badbaby/` has lots of anomalies / redundancies. It gets rsync'd to `/storage/badbaby-redux/server-data`.

- file and folder naming anomalies and known-bad-file exclusions are handled by `select-files-from-*.py`


## Data prep

There is a `Makefile` in the `prep-dataset` folder. `make all` will:

1. rsync data from local and remote sources.
2. sort through the copied file trees, generate a mapping from filenames we want to keep to new file locations (correcting folder- or file-names along the way), and make a hardlink to each "kept" file at the new location.
3. write summaries of how much data we have for each subject/session.
4. generate logs / lists of missing or unexpected files.


## Converting to BIDS

The script `prep-dataset/bidsify.py` will convert the dataset to BIDS format in folder `bids-data`. It can also check/validate the events found in the FIF files against the TAB files from the stimulus presentation script (enabled in the `bidsify.py` script via a boolean flag). Any failures to match up events from the FIF and TAB files will be flagged in `prep-dataset/qc/log-of-scoring-issues.txt`.

# TODOS

- [ ] there are still some pairs of `-raw.fif` and `-raw2.fif` for the same subject/session. Need to check logs and/or view files to determine which to use (we shouldn't use both!)
