# Bad Baby reanalysis

This repo is for reanalysis of the "Bad Baby" data, using the MNE-BIDS-Pipeline.

## Data prep

1. `sudo rsync-data-from-local-untitled-drive.sh`
2. `rsync-data-from-server.sh`
3. `python select-files-from-local.py`
4. `python select-files-from-server.py`
5. `python make-hardlinks.py > qc/log-of-hardlinking.txt`

4. `python qc/find-surrogate-erms.py`
5. `qc/copy-surrogate-erms.sh`
6. `catalog-data-completeness.py local > summary-of-what-came-from-local-drive.txt`
7. `catalog-data-completeness.py munged > summary-of-what-we-have-after-munging.txt`
