#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SUBDIR=bids-data/derivatives/mne-bids-pipeline

set -exo pipefail

# Epochs, forward, cov, rank
rsync -avP \
    --include="sub-*/" --include="sub-*/ses-*/" --include="sub-*/ses-*/meg/" \
    --include="**/*_epo.fif" \
    --include="**/*_fwd.fif" \
    --include="**/*_cov.fif" \
    --include="**/*_rank.json" \
    --exclude="*" --prune-empty-dirs \
    bieber:/storage/badbaby-redux/$SUBDIR/ $SCRIPT_DIR/../$SUBDIR/
