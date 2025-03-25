#!/bin/bash
set -euf -o pipefail

if [ $# -lt 2 ]
then
    echo "USAGE: run-pipeline.sh EXPERIMENT_NAME PREPOST"
    echo "    allowed values for EXPERIMENT_NAME:"
    echo "        am, mmn, ids"
    echo "    allowed values for PREPOST:"
    echo "        pre, post (refers to wither ICA component selection is already done or not),"
    echo "        or 'copy' to transfer ICA bads from YAML file into corresponding derivatives files,"
    echo "        or any valid MNE-BIDS-pipeline step name"
    exit 0
fi

case "$1" in
    am | mmn | ids)
        ;;
    *)
        echo "first argument must be one of: am, mmn, ids"
        exit 1
        ;;
esac

case "$2" in
    init | preprocessing | sensor | source | freesurfer)
        STEPS="$2"
        ;;
    pre)
        STEPS=init,preprocessing/_01_data_quality,preprocessing/_02_head_pos,preprocessing/_03_maxfilter,preprocessing/_04_frequency_filter,preprocessing/_05_regress_artifact,preprocessing/_06b_run_ssp,preprocessing/_07_make_epochs
        ;;
    post)
        STEPS=preprocessing/_08b_apply_ssp,preprocessing/_09_ptp_reject,sensor,source
        ;;
    all)
        STEPS=init,preprocessing,sensor,source
        ;;
    *)
        echo "second argument must be one of: pre, post, init, preprocessing, sensor, source, freesurfer"
        exit 1
        ;;
esac

xvfb-run mne_bids_pipeline --config "$1.py" --steps=$STEPS "${@:3}"
