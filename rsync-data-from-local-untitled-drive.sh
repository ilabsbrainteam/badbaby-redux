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
# --include='bad*_raw2.fif'     keep _raw2.fif
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
    --include='bad*_raw2.fif' \
    --include='bad*_prebad.txt' \
    --exclude='*' \
    /media/mdclarke/Untitled/ $DESTDIR

# fix bad folder name. The datestamp here indicates that this is actually
# bad_208 (not bad_208a), cf. the existence of:
# /mnt/brainstudio/bad_baby/bad_208/151007 and
# /mnt/brainstudio/bad_baby/bad_208a/151015
# however, note the two recordings are only 8 days apart; double-check whether
# the earlier date is still within age criterion for "a" sessions; if so, use it.
mkdir -p $DESTDIR/bad_208/raw_fif
mv $DESTDIR/bad_208a/151007/* $DESTDIR/bad_208/raw_fif/
rmdir $DESTDIR/bad_208a/151007

# fix bad filename (208a → 208b, to match containing folder).
# Assumption here is that a typo is more likely than storing a file from run "a" in the
# folder from run "b", since a folder for run "b" wouldn't have existed at the time
# run "a" files were saved.
pushd $DESTDIR/bad_208b/raw_fif/
mv bad_208a_erm_raw.fif bad_208b_erm_raw.fif
popd

# copy files with bad filenames (*_erm.fif instead of *_erm_raw.fif)
pushd /media/mdclarke/Untitled/bad_208a/151007/
cp -n bad_208_erm.fif $DESTDIR/bad_208/raw_fif/bad_208_erm_raw.fif
popd

pushd /media/mdclarke/Untitled/bad_314b/raw_fif/
cp -n bad_314b_erm.fif $DESTDIR/bad_314b/raw_fif/bad_314b_erm_raw.fif
popd

pushd /media/mdclarke/Untitled/bad_316b/raw_fif/
cp -n bad_316b_erm.fif $DESTDIR/bad_316b/raw_fif/bad_316b_erm_raw.fif
popd

# these two we know that `raw.fif` is corrupted and `raw2.fif` is good
pushd $DESTDIR/bad_128a/raw_fif/
mv bad_128a_ids_raw2.fif bad_128a_ids_raw.fif
popd

pushd $DESTDIR/bad_208a/raw_fif/
mv bad_208_ids_raw2.fif bad_208_ids_raw.fif
popd

# there are 2 ERMs in bad_209b; files are identical; one has wrong subj name (208b);
# the folder for 208b already has an ERM of different file size; therefore delete the duplicate.
rm $DESTDIR/bad_209b/raw_fif/bad_208b_erm_raw.fif

chown -R $USER $DESTDIR
chgrp -R badbaby $DESTDIR

# copy over to "data" as hardlinks
cp -al $DESTDIR/* data/
