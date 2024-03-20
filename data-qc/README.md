# Notes on data sources and data munging

- local folder `/media/mdclarke/Untitled` contains badbaby data with `prebad` files defined and many missing emptyroom files tracked down. This is our starting point, copied to `/storage/badbaby-redux/local-data` (via `../rsync-data-from-local-untitled-drive.sh`) and then hardlinked from `/storage/badbaby-redux/data`

- running `catalog-data-completeness.py local` leaves a record (`files-in-local-data.csv`) of which files originated locally, in case we need it. It also writes a summary to stdout when run, which I've redirected to a file for posterity (`summary-of-what-came-from-local-drive.txt`).

- server folder `/mnt/brainstudio/badbaby/` has lots of anomalies / redundancies. Script `../rsync-data-from-server.sh` copies the necessary data to `/storage/badbaby-redux/server-data` and cleans it up a bit.

- script `../fill-gaps-from-local-with-server-data.py` assesses what is present in server data that is missing from local data, and fills in the gaps. Along the way, it renames some files when the subject ID in the filename mismatches the subject ID in the containing foldername. Only does this if the subject ID in the filename is not an attested subject ID (e.g., is clearly a typo). A log of its output showing what was *not* copied is in `log-of-gap-filling-failures.txt`

- after filling the gaps, running `catalog-data-completeness.py munged` will generate logs (`files-in-data.csv`) and summaries (`summary-of-what-we-have-after-munging.txt`) of the data for the *combined* data (local and server).
