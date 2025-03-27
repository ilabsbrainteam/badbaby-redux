#!/bin/bash

SUBJECTS_DIR=/storage/badbaby-redux/bids-data/derivatives/freesurfer/subjects
# (out|inn)er_sk(in|ull).surf
find $SUBJECTS_DIR -name *er_sk*.surf -delete
