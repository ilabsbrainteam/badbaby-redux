#!/bin/bash
set -e

export DESTDIR=/storage/badbaby-redux/local-data
mkdir -p $DESTDIR

# --include='/bad_*a/'          keep all bad_NNNa folders
# --include='/bad_*b/'          keep all bad_NNNb folders
# --exclude='/*/'               skip all other root-level folders (plot*, .fseventsd, etc)
# --include='raw_fif/'          consider only the raw data files
# --include='151007/'           for subj 208a; should be "raw_fif" but isn't
# --exclude='bad*_otp_raw.fif'  skip OTP-processed files
# --include='bad*_raw.fif'      keep _raw.fif
# --include='bad*_raw2.fif'     keep (mis-named) _raw2.fif
# --include='bad*_erm.fif'      keep (mis-named) _erm.fif
# --include='bad*_prebad.txt'   keep prebads
# --exclude='*'                 skip all other files

rsync -rtvzm --partial --progress --delete --chown $USER:badbaby \
    --include='/bad_*a/' \
    --include='/bad_*b/' \
    --exclude='/*/' \
    --include='raw_fif/' \
    --include='151007/' \
    --exclude='bad*_otp_raw.fif' \
    --include='bad*_raw.fif' \
    --include='bad*_raw2.fif' \
    --include='bad*_erm.fif' \
    --exclude='*' \
    /media/mdclarke/Untitled/ $DESTDIR
