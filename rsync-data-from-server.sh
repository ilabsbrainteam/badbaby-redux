#!/bin/sh

export DESTDIR=server-data
mkdir -p $DESTDIR

# --exclude='/bad_baby/'     avoid redundant root-level folder containing partial duplicate of dataset
# --include='/bad_*/'        keep all other bad_* folders
# --exclude='/*/'            skip all other root-level folders (pilot*, eric*, otso*)
# --include='*/'             include subfolders within the bad_*/ dirs
# --include='bad*_raw.fif'   keep _raw.fif
# --exclude='*'              skip all other files

rsync -rtvzm --partial --progress \
    --exclude='/bad_baby/' \
    --include='/bad_*/' \
    --exclude='/*/' \
    --include='*/' \
    --include='bad*_raw.fif' \
    --exclude='*' \
    /mnt/brainstudio/bad_baby/ ./$DESTDIR/


# this tells us that there aren't any prebad .txt files (only shows a few PNG, TIFF, PDF):
# find /mnt/brainstudio/bad_baby -type f -wholename '/mnt/brainstudio/bad_baby/bad_*/**/*' | grep -v '.fif$'

# there are also no trans files:
# find /mnt/brainstudio/bad_baby -type f -name '*trans.fif'
