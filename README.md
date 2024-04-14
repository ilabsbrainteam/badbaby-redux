# Bad Baby reanalysis

This repo is for reanalysis of the "Bad Baby" data, using the MNE-BIDS-Pipeline.

## Data prep

1. `rsync-data-from-local-untitled-drive.sh` (may need `sudo`)
2. `rsync-data-from-server.sh`
3. `python select-files-from-local.py`
4. `python select-files-from-server.py`
5. `python make-hardlinks.py > qc/log-of-hardlinking.txt`
6. `cd qc/`
    - `python catalog-data-completeness.py local > summary-of-local-drive.txt`
    - `python catalog-data-completeness.py combined > summary-combined-data-sources.txt`
    - `python find-surrogate-erms.py > log-of-surrogate-erms.txt`
    - `python link-surrogate-erms.py`
    - now repeat `python catalog-data-completeness.py combined > summary-after-linking-erms.txt`
