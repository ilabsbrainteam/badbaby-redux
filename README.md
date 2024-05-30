# Bad Baby reanalysis

This repo is for reanalysis of the "Bad Baby" data, using the MNE-BIDS-Pipeline.


## Notes on data sources and data munging

- local folder `/media/<REDACTED>/Untitled` contains badbaby data with `prebad` files defined and many missing emptyroom files tracked down. This is our starting point, rsync'd to `./local-data`.

- server folder `/mnt/brainstudio/badbaby/` has lots of anomalies / redundancies. It gets rsync'd to `./server-data`.

- file and folder naming anomalies and known-bad-file exclusions are handled by `prep-dataset/select-files-from-*.py`


## Data prep

There is a `Makefile` in the `prep-dataset` folder. `make all` will:

1. rsync data from local and remote sources.
2. sort through the copied file trees, generate a mapping from filenames we want to keep to new file locations (correcting folder- or file-names along the way), and make a hardlink to each "kept" file at the new location.
3. write summaries of how much data we have for each subject/session.
4. generate logs / lists of missing or unexpected files.


## Converting to BIDS

The script `prep-dataset/bidsify.py` will convert the dataset to BIDS format in folder `bids-data`. It also checks/validates the events found in the FIF files against the TAB files from the stimulus presentation script (enabled in the `bidsify.py` script via a boolean flag `verify_events_against_tab_files`). Any failures to match up events from the FIF and TAB files will be flagged in `prep-dataset/qc/log-of-scoring-issues.txt`.

# TODOS

- [ ] coreg
- [ ] add the MRIs to `bidsify.py` (or write a separate script to add them to the bids tree?)
- [ ] setup MNE-BIDS-pipeline to do the preprocessing
