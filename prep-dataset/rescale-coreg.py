#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Automated coregistration.
authors: Daniel McCloy
license: MIT
"""

from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from yaml import safe_load

import mne
from mne.io.constants import FIFF
import numpy as np
import pandas as pd

# configurable params
qc = False
scaling_already_done = False
do_nasion_shift = True
nasion_shift_xyz = np.array([0, 0, 0.03])  # in meters!

# path stuff
root = Path("/storage/badbaby-redux").resolve()
subjects_dir = root / "anat"
data_dir = root / "data"
prep_dir = root / "prep-dataset"
outdir = prep_dir / "qc"
subjects = sorted(path.name for path in data_dir.glob("bad_*"))
subjects_dir.mkdir(exist_ok=True)

with open(prep_dir / "misplaced-nasion.yaml") as fid:
    nasion_sub_ses = safe_load(fid)

# init logging (erase old log files)
mri_log = outdir / "log-of-MRI-scaling-issues.txt"
with open(mri_log, "w") as fid:
    pass

# ensure we have the surrogate MRI files downloaded (won't re-download if already there)
surrogates = dict()
surrogate_age = np.array([2, 3, 4.5, 6])
surrogate_age_str = tuple(f"{x:g}mo" for x in surrogate_age)
for age in surrogate_age_str:
    surrogates[age] = mne.datasets.fetch_infant_template(age, subjects_dir=subjects_dir)

# load DOB data
ages = pd.read_csv(root / "metadata" / "subj-dob.csv", header=0, index_col="subj")
ages = ages.map(pd.to_datetime)
gestational_or_birth = "gestational"  # gestational or birth
days_per_month = np.mean([28.25] + [30] * 4 + [31] * 7)

# generate the MRI config files for scaling surrogate MRI to individual
# subject's digitization points. Then scale the MRI and make the BEM solution.
for subject in subjects:
    if scaling_already_done:
        break
    # terminal message
    msg = "PROCESSING SUBJECT"
    msg_width = len(msg) + max(map(len, subjects)) + 5
    print("#" * msg_width)
    print(f"# {msg} {subject: <4} #")
    print("#" * msg_width)
    # basics
    int_subj = int(subject.lstrip("bad_").rstrip("ab"))
    this_subj_dir = data_dir / subject / "raw_fif"
    session = subject[-1] if subject[-1] in "ab" else "c"

    # we need to potentially handle each task recording separately, because some subjs
    # did some tasks on different day (thus different digitizations / different coregs)
    meas_dates = defaultdict(list)
    for task in ("am", "ids", "mmn"):
        raw_fname = this_subj_dir / f"{subject}_{task}_raw.fif"
        if raw_fname.exists():
            info = mne.io.read_info(raw_fname, verbose=False)
            meas_date = info["meas_date"].date()
            meas_dates[meas_date].append(task)

    # now we can properly triage which task(s) need separate coregs based on meas_date
    for meas_date, tasks in meas_dates.items():
        # is this a meas_date with only 1 task? If so it needs its own trans/coreg
        extra_session = len(meas_dates) > 1 and len(tasks) == 1
        # get age in days at time of recording
        age = (meas_date - ages.loc[int_subj, gestational_or_birth].date()).days
        _2mo = 2 * days_per_month
        _6mo = 6 * days_per_month
        msg = (
            f"{subject: <4} was {age} days ({gestational_or_birth} age) at recording "
            "(expected {low}-{high} days)\n"
        )
        # choose correct surrogate
        if session in "ab":
            surrogate = f"ANTS{3 if session == 'a' else 6}-0Months3T"
            target_age = _2mo if session == "a" else _6mo
            lo, hi = np.array([-7, 7]) + target_age
            if not lo <= age <= hi:
                with open(mri_log, "a") as fid:
                    fid.write(msg.format(low=int(lo), high=int(np.ceil(hi))))
        else:
            ix = np.argmin(np.abs(surrogate_age - age / days_per_month))
            surrogate = surrogates[surrogate_age_str[ix]]

        # Most subjs have all tasks on the same meas_date, so only specify task in
        # folder/filename if needed (like we did for ERM)
        subject_to = f"{subject}_{tasks[0]}" if extra_session else subject

        # shift the nasion
        fiducials = "auto"
        needs_shift = (
            str(int_subj) in nasion_sub_ses and session in nasion_sub_ses[str(int_subj)]
        )
        if do_nasion_shift and needs_shift:
            fids_path = subjects_dir / surrogate / "bem" / f"{surrogate}-fiducials.fif"
            fiducials, coord_frame = mne.io.read_fiducials(fids_path)
            assert coord_frame == FIFF.FIFFV_COORD_MRI, coord_frame
            idx = [
                ix
                for ix, p in enumerate(fiducials)
                if p["ident"] == FIFF.FIFFV_POINT_NASION
                and p["kind"] == FIFF.FIFFV_POINT_CARDINAL
            ]
            idx = np.array(idx).item()
            # need deepcopy because `r` array has flags OWNDATA=False, WRITEABLE=False
            nasion = deepcopy(fiducials[idx])
            nasion["r"] += nasion_shift_xyz
            nasion["r"].setflags(write=False)
            fiducials[idx] = nasion

        # run automated coreg
        raw_fname = this_subj_dir / f"{subject}_{tasks[0]}_raw.fif"
        info = mne.io.read_info(raw_fname, verbose=False)
        coreg = mne.coreg.Coregistration(
            info, subject=surrogate, subjects_dir=subjects_dir, fiducials=fiducials
        )
        coreg.set_scale_mode("3-axis")
        coreg.set_fid_match("matched")  # TODO consider using "nearest"?
        coreg.fit_fiducials()
        n_pts = coreg.compute_dig_mri_distances().size
        # do ICP fitting, and drop far-away points
        coreg.fit_icp(n_iterations=10)
        for dist in (10e-3, 5e-3):  # 10mm, 5mm
            coreg.omit_head_shape_points(distance=dist)
            # if any points were actually dropped, refit
            if new_n_pts := coreg.compute_dig_mri_distances().size < n_pts:
                coreg.fit_icp(n_iterations=10)
                n_pts = new_n_pts

        # scale the MRI (and save it to `subjects_dir`). This step takes a while.
        mne.scale_mri(
            subject_from=surrogate,
            subject_to=subject_to,
            scale=coreg.scale,
            overwrite=True,
            labels=True,
            annot=True,
            subjects_dir=subjects_dir,
            verbose=True,
        )
        # save the trans file
        trans_fpath = subjects_dir / subject_to / f"{subject_to}_trans.fif"
        mne.write_trans(trans_fpath, coreg.trans, overwrite=True)

        # make BEM solution. We only need 1-layer, but the 6mo surrogate only has
        # 3-layer so let's use that for everyone
        bem_dir = subjects_dir / subject_to / "bem"
        bem_in = bem_dir / f"{subject_to}-5120-5120-5120-bem.fif"
        bem_inout_1 = bem_dir / f"{subject_to}-5120-bem.fif"
        bem_out_3 = bem_dir / f"{subject_to}-5120-5120-5120-bem-sol.fif"
        bem_out_1 = bem_dir / f"{subject_to}-5120-bem-sol.fif"
        solution = mne.make_bem_solution(bem_in)
        mne.write_bem_solution(bem_out_3, solution)
        # we also want a 1-layer BEM to satisify MNE-BIDS-Pipeline
        # we could add a config value for MNE-BIDS-Pipeline, but the
        bem_surfaces = mne.read_bem_surfaces(bem_in)[-1:]
        mne.write_bem_surfaces(bem_inout_1, bem_surfaces)
        assert bem_surfaces[0]["id"] == mne.io.constants.FIFF.FIFFV_BEM_SURF_ID_BRAIN, \
            f"{bem_surfaces[0]["id"]=} != {mne.io.constants.FIFF.FIFFV_BEM_SURF_ID_BRAIN}"
        solution_1 = mne.make_bem_solution(bem_inout_1)
        mne.write_bem_solution(bem_out_1, solution_1)

# QC the coregistrations
if qc:
    for subject in subjects:
        # any raw file will do, just need its Info
        this_subj_dir = data_dir / subject / "raw_fif"
        raw_fname = next(this_subj_dir.glob(f"{subject}_*_raw.fif"))
        info = mne.io.read_info(raw_fname, verbose=False)
        # load trans
        task = raw_fname.name.split("_")[-2]
        assert task in ("am", "mmn", "ids"), task
        # try the task-specific filename first...
        try:
            trans = mne.read_trans(
                subjects_dir / f"{subject}_{task}" / f"{subject}_{task}_trans.fif"
            )
        # ...if it doesn't exist, the non-task-specific is the correct one
        except FileNotFoundError:
            trans = mne.read_trans(subjects_dir / subject / f"{subject}_trans.fif")
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
