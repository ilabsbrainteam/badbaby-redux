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


## Converting to BIDS

The script `prep-dataset/bidsify.py` will convert the dataset in `./data` to BIDS format in `./bids-data`. It also checks/validates the events found in the FIF files against the TAB files from the stimulus presentation script (enabled in the `bidsify.py` script via a boolean flag `verify_events_against_tab_files`). Any failures to match up events from the FIF and TAB files will be flagged in `prep-dataset/qc/log-of-scoring-issues.txt`.

## Running the Pipeline

Files related to the preprocessing pipeline are in `./pipeline`.
The bash script `run-pipeline.sh` can be invoked in a few different ways. Here is the intended workflow:

- `./run-pipeline.sh am pre` will process the AmplitudeModulatedTones (`am`) data using the config file `am.py`, and will run the pipeline steps up through ICA decomposition.
- View the pipeline reports at `./bids-data/derivatives/mne-bids-pipeline/sub-XXX/ses-Z/meg/sub-XXX_ses-Y_task-AmplitudeModulatedTones_report.html` to determine which ICA components to exclude.
- Mark the bad components in `bad-ICA-components-am.yaml`.
- When you're done marking bad ICA components, run `./run-pipeline.sh am copy` to automatically transfer the ICA component statuses to `./bids-data/derivatives/mne-bids-pipeline/sub-XXX/ses-Z/meg/sub-XXX_ses-Y_task-ZZZZZZ_proc-ica_components.tsv`. It's done this way so that you can safely wipe out the `./bids-data/derivatives/mne-bids-pipeline` folder and re-run the pipeline from scratch, without losing prior ICA component annotations --- though beware that you cannot safely assume component numbers will be stable across runs! Still, it may be useful to be able to see how many components you excluded last time, even if the numbers must change.
- Now you can run `./run-pipeline.sh am post` to run all the post-ICA preprocessing steps.
