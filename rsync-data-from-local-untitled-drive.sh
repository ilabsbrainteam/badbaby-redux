#!/bin/sh

export DESTDIR=local-data
mkdir -p $DESTDIR

# --include='/bad_*a/'          keep all bad_NNNa folders
# --include='/bad_*b/'          keep all bad_NNNb folders
# --exclude='/*/'               skip all other root-level folders (plot*, .fseventsd, etc)
# --include='raw_fif/'          consider only the raw data files
# --include='151007/'           for subj 208a; should be "raw_fif" but isn't
# --exclude='bad*_otp_raw.fif'  skip OTP-processed files
# --include='bad*_raw.fif'      keep _raw.fif
# --include='bad*_prebad.txt'   keep prebads
# --exclude='*'                 skip all other files

rsync -rtvzm --partial --progress \
    --include='/bad_*a/' \
    --include='/bad_*b/' \
    --exclude='/*/' \
    --include='raw_fif/' \
    --include='151007/' \
    --exclude='bad*_otp_raw.fif' \
    --include='bad*_raw.fif' \
    --include='bad*_prebad.txt' \
    --exclude='*' \
    /media/mdclarke/Untitled/ ./$DESTDIR

# fix the bad folder name
mv ./$DESTDIR/bad_208a/151007/ ./$DESTDIR/bad_208a/raw_fif/
