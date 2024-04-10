#!/bin/bash
set -e

export DESTDIR=/storage/badbaby-redux/server-data
mkdir -p $DESTDIR

# --exclude='/bad_baby/'     avoid redundant root-level folder containing partial duplicate of dataset
# --include='/bad_*/'        keep all other bad_* folders
# --exclude='/*/'            skip all other root-level folders (pilot*, eric*, otso*)
# --include='*/'             include subfolders within the bad_*/ dirs
# --include='bad*_raw.fif'   keep _raw.fif
# --include='bad*_raw2.fif'  keep _raw2.fif
# --exclude='*'              skip all other files

rsync -rtvzm --partial --progress \
    --exclude='/bad_baby/' \
    --include='/bad_*/' \
    --exclude='/*/' \
    --include='*/' \
    --include='bad*_raw.fif' \
    --include='bad*_raw2.fif' \
    --exclude='*' \
    /mnt/brainstudio/bad_baby/ $DESTDIR/


# this tells us that there aren't any prebad .txt files (only shows a few PNG, TIFF, PDF):
# find /mnt/brainstudio/bad_baby -type f -wholename '/mnt/brainstudio/bad_baby/bad_*/**/*' | grep -v '.fif$'

# there are also no trans files:
# find /mnt/brainstudio/bad_baby -type f -name '*trans.fif'

# fix bad filename (bad_baby_* instead of bad_*)
pushd $DESTDIR/bad_202/150916
mv bad_baby_202_ids_raw2.fif bad_202_ids_raw2.fif
popd

# delete redundant file (has extra "_bad_" in filename; correctly-named file exists in same directory and is larger)
rm $DESTDIR/bad_311a/160126/bad_311a_mmn_bad_raw.fif

# delete redundant file (missing "_mmn" in filename; correctly-named file exists from local, and has same size)
rm $DESTDIR/bad_129a/160129/bad_129a_raw.fif

# fix bad folder name (and file name!)
mkdir -p $DESTDIR/bad_208a/151015
mv $DESTDIR/bad_208_a/151015/bad_208_mmn_raw.fif $DESTDIR/bad_208a/151015/bad_208a_mmn_raw.fif
rm -r $DESTDIR/bad_208_a

# fix bad filename (bad_208b_erm_raw.fif inside folder for 209b)
# there's already an ERM for 209b in the local data, and it has identical file size to this one.
#Therefore, presumed to be a filename typo / duplicate.
pushd $DESTDIR/bad_209b/160219
mv bad_208b_erm_raw.fif bad_209b_erm_raw.fif
popd

# also prevent file from second MEG session from clobbering earlier run
pushd $DESTDIR/bad_209b/160225
mv bad_209b_mmn_raw.fif bad_209b_mmn_raw2.fif

# remove redundant data (232a inside 222a; 232a data exists up a level, in its own folder)
rm -r $DESTDIR/bad_222a/bad_232a/

# remove a "perhaps duplicate" folder, but first copy any files missing from the non-duplicate folder
# (files with same names were first confirmed to have identical file sizes)
mv -n $DESTDIR/bad_104/151009perhapsduplicate/* $DESTDIR/bad_104/151009/
rm -r $DESTDIR/bad_104/151009perhapsduplicate/

sudo chown -R $USER $DESTDIR
sudo chgrp -R badbaby $DESTDIR
