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

# fix bad folder name. The datestamp here indicates that this is actually
# bad_208 (not bad_208a), cf. the existence of:
# /mnt/brainstudio/bad_baby/bad_208/151007 and
# /mnt/brainstudio/bad_baby/bad_208a/151015
# however, note the two recordings are only 8 days apart; double-check whether
# the earlier date is still within age criterion for "a" sessions; if so, use it.
mv ./$DESTDIR/bad_208a/151007/ ./$DESTDIR/bad_208/raw_fif/

# fix bad filename (208a → 208b, to match containing folder).
# Assumption here is that a typo is more likely than storing a file from run "a" in the
# folder from run "b", since a folder for run "b" wouldn't have existed at the time
# run "a" files were saved.
pushd ./$DESTDIR/bad_208b/raw_fif/
mv bad_208a_erm_raw.fif bad_208b_erm_raw.fif
popd

# copy files with bad filenames (not caught by our rsync)
pushd /media/mdclarke/Untitled/bad_208a/151007/
cp bad_208_erm.fif $DESTDIR/bad_208/bad_208_erm_raw.fif
popd

pushd /media/mdclarke/Untitled/bad_314b/raw_fif/
cp bad_314b_erm.fif $DESTDIR/bad_314b/bad_314b_erm_raw.fif
popd

pushd /media/mdclarke/Untitled/bad_316b/raw_fif/
cp bad_316b_erm.fif $DESTDIR/bad_316b/bad_316b_erm_raw.fif
popd

# these will need further action to decide if they're usable
pushd /media/mdclarke/Untitled/bad_128a/raw_fif/
cp bad_128a_ids_raw2.fif $DESTDIR/bad_128a/raw_fif/
popd

pushd /media/mdclarke/Untitled/bad_208a/151007/
cp bad_208_ids_raw2.fif $DESTDIR/bad_208/raw_fif/
popd

# copy over to "data" as hardlinks
cp -al $DESTDIR/* data/
