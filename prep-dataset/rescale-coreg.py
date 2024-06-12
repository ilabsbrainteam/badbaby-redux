#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Automated coregistration.
authors: Daniel McCloy
license: MIT
"""

from pathlib import Path

import mne
from mne.io.constants import FIFF
import numpy as np

# configurable params
qc = False
scaling_already_done = False
do_nasion_shift = False
nasion_shift_xyz = np.array([0, 0, 0.03])  # in meters!

# path stuff
root = Path("/storage/badbaby-redux").resolve()
subjects_dir = root / "anat"
data_dir = root / "data"
subjects = sorted(path.name for path in data_dir.glob("bad_*"))

# ensure we have the surrogate MRI files downloaded (won't re-download if already there)
for age in ("2mo", "3mo", "6mo"):
    _ = mne.datasets.fetch_infant_template(age, subjects_dir=subjects_dir)

# generate the MRI config files for scaling surrogate MRI to individual
# subject's digitization points. Then scale the MRI and make the BEM solution.
for subject in subjects:
    if scaling_already_done:
        break
    # choose correct surrogate
    if subject.endswith("a"):
        surrogate = "ANTS3-0Months3T"
    elif subject.endswith("b"):
        surrogate = "ANTS6-0Months3T"
    else:
        # TODO we can/should get the ages from somewhere and scale these too
        print(f"AGE NOT KNOWN FOR SUBJECT {subject}, CAN'T AUTO-SELECT SURROGATE MRI")
        continue
    # terminal message
    msg = "NOW SCALING SUBJECT"
    msg_width = len(msg) + max(map(len, subjects)) + 5
    print("#" * msg_width)
    print(f"# {msg} {subject: <4} #")
    print("#" * msg_width)
    # any raw file will do, just need its Info
    this_subj_dir = data_dir / subject / "raw_fif"
    files = this_subj_dir.glob(f"{subject}_*_raw.fif")
    raw_fname = next(files)
    while raw_fname.match("*_erm_*"):
        raw_fname = next(files)
    info = mne.io.read_info(raw_fname, verbose=False)
    # shift the nasion
    if do_nasion_shift:
        nasion = next(p for p in info["dig"] if p["ident"] == FIFF.FIFFV_POINT_NASION)
        nasion["r"] += nasion_shift_xyz
    # run automated coreg
    coreg = mne.coreg.Coregistration(info, subject=surrogate, subjects_dir=subjects_dir)
    coreg.set_scale_mode("3-axis")
    coreg.set_fid_match("matched")  # TODO consider using "nearest"?
    coreg.fit_fiducials()  # TODO consider reducing nasion weight?
    n_pts = coreg.compute_dig_mri_distances().size
    # do ICP fitting, and drop far-away points
    coreg.fit_icp(n_iterations=10)
    for dist in (10e-3, 5e-3):  # 10mm, 5mm
        coreg.omit_head_shape_points(distance=dist)
        # if any points were actually dropped, refit
        if new_n_pts := coreg.compute_dig_mri_distances().size < n_pts:
            coreg.fit_icp(n_iterations=10)
            n_pts = new_n_pts
    # save the trans file
    trans_fname = this_subj_dir / f"{subject}-trans.fif"
    mne.write_trans(trans_fname, coreg.trans, overwrite=True)
    # this step takes a while
    mne.scale_mri(
        subject_from=surrogate,
        subject_to=subject,
        scale=coreg.scale,
        overwrite=True,
        labels=True,
        annot=True,
        subjects_dir=subjects_dir,
        verbose=True,
    )
    # make BEM solution. We only need 1-layer, but the 6mo surrogate only has 3-layer
    # so let's use that for everyone
    bem_in = subjects_dir / subject / "bem" / f"{subject}-5120-5120-5120-bem.fif"
    bem_out = subjects_dir / subject / "bem" / f"{subject}-5120-5120-5120-bem-sol.fif"
    solution = mne.make_bem_solution(bem_in)
    mne.write_bem_solution(bem_out, solution)

# QC the coregistrations
if qc:
    for subject in subjects:
        # any raw file will do, just need its Info
        this_subj_dir = data_dir / subject / "raw_fif"
        raw_fname = next(this_subj_dir.glob(f"{subject}_*_raw.fif"))
        info = mne.io.read_info(raw_fname, verbose=False)
        # load trans
        trans_fname = this_subj_dir / f"{subject}-trans.fif"
        trans = mne.read_trans(trans_fname)
        # plot
        mne.viz.plot_alignment(
            info=info,
            trans=trans,
            subject=subject,
            subjects_dir=subjects_dir,
            surfaces=dict(head=0.9),
            dig=True,
            mri_fiducials=True,
            meg=False,
        )
        # user interaction
        spaces = " " * (len(subject) + 14)
        response = input(
            f"Now viewing {subject}; press <ENTER> to continue;\n"
            f"{spaces}press C <ENTER> to run manual coreg\n"
            f"{spaces}press X <ENTER> to quit\n"
        )
        if response.lower().startswith("x"):
            break
        elif response.lower().startswith("c"):
            # run coregistration GUI to do it manually and compare
            mne.gui.coregistration(
                inst=raw_fname,
                subject=surrogate,
                subjects_dir=subjects_dir,
                guess_mri_subject=False,
                mark_inside=True,
            )
