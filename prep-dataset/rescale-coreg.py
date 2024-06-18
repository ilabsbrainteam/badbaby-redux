#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Automated coregistration.
authors: Daniel McCloy
license: MIT
"""

from collections import defaultdict
from pathlib import Path

import mne
from mne.io.constants import FIFF
import numpy as np
import pandas as pd

# configurable params
qc = False
scaling_already_done = False
do_nasion_shift = False
nasion_shift_xyz = np.array([0, 0, 0.02])  # in meters!

# path stuff
root = Path("/storage/badbaby-redux").resolve()
subjects_dir = root / "anat"
data_dir = root / "data"
outdir = root / "prep-dataset" / "qc"
subjects = sorted(path.name for path in data_dir.glob("bad_*"))

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

        # # TODO temporary hack to avoid re-running subjs when debugging
        # sub = f"{subject}_{task}" if extra_session else subject
        # if (subjects_dir / sub / "bem" / f"{sub}-5120-5120-5120-bem-sol.fif").exists():
        #     continue
        # # TODO end TODO

        # get age in days at time of recording
        age = (meas_date - ages.loc[int_subj, gestational_or_birth].date()).days
        _2mo = 2 * days_per_month
        _6mo = 6 * days_per_month
        msg = (
            f"{subject: <4} was {age} days ({gestational_or_birth} age) at recording "
            "(expected {low}-{high} days)\n"
        )
        # choose correct surrogate
        if subject[-1] in "ab":
            surrogate = f"ANTS{3 if subject.endswith('a') else 6}-0Months3T"
            target_age = _2mo if subject.endswith("a") else _6mo
            lo, hi = np.array([-7, 7]) + target_age
            if not lo <= age <= hi:
                with open(mri_log, "a") as fid:
                    fid.write(msg.format(low=int(lo), high=int(np.ceil(hi))))
        else:
            ix = np.argmin(np.abs(surrogate_age - age / days_per_month))
            surrogate = surrogates[surrogate_age_str[ix]]

        # shift the nasion (needs info)
        raw_fname = this_subj_dir / f"{subject}_{tasks[0]}_raw.fif"
        info = mne.io.read_info(raw_fname, verbose=False)
        if do_nasion_shift:
            try:
                nasion = next(
                    p for p in info["dig"] if p["ident"] == FIFF.FIFFV_POINT_NASION
                )
            except StopIteration:
                raise RuntimeError(f"{raw_fname.name} is missing nasion!!") from None
            nasion["r"] += nasion_shift_xyz

        # run automated coreg
        coreg = mne.coreg.Coregistration(
            info, subject=surrogate, subjects_dir=subjects_dir
        )
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

        # save the trans file and scale the MRI. Most subjs have all tasks on the same
        # meas_date, so only specify task in filename if needed (like we did for ERM)
        trans_fname = this_subj_dir / f"{subject}_trans.fif"
        subject_to = subject
        if extra_session:
            trans_fname = this_subj_dir / f"{subject}_{task}_trans.fif"
            subject_to = f"{subject}_{task}"
        mne.write_trans(trans_fname, coreg.trans, overwrite=True)
        # this step takes a while
        mne.scale_mri(
            subject_from=surrogate,
            subject_to=subject_to,
            scale=coreg.scale,
            overwrite=False,
            labels=True,
            annot=True,
            subjects_dir=subjects_dir,
            verbose=True,
        )

        # make BEM solution. We only need 1-layer, but the 6mo surrogate only has
        # 3-layer so let's use that for everyone
        bem_dir = subjects_dir / subject_to / "bem"
        bem_in = bem_dir / f"{subject_to}-5120-5120-5120-bem.fif"
        bem_out = bem_dir / f"{subject_to}-5120-5120-5120-bem-sol.fif"
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
