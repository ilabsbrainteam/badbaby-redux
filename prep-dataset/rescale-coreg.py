#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Automated coregistration.
authors: Daniel McCloy
license: MIT
"""

import argparse
from collections import defaultdict
from pathlib import Path
from yaml import safe_load

import mne
from mne.io.constants import FIFF
import numpy as np
import pandas as pd

from utils import hardlink

parser = argparse.ArgumentParser(
    description="Create scaled anatomies for badbaby data",
)
parser.add_argument("SUBJECTS", type=str, nargs="*", help="Subject IDs to process",)
args = parser.parse_args()
subjects_to_process = set(args.SUBJECTS)

# configurable params
qc = False
scaling_already_done = True
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

bad = set(subjects_to_process) - set(subjects)
if bad:
    raise RuntimeError(f"Specified subjects do not exist: {sorted(bad)}")

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

good_fiducials = {
    "ANTS2-0Months3T": [
        [-43, -2, -9],  # LPA
        [3, 52, 11],  # Nasion
        [50, -1, -7],  # RPA
    ],
    "ANTS3-0Months3T": [
        [-52, -6, -27],  # LPA
        [2, 60, -17],  # Nasion
        [59, -3, -26],  # RPA
    ],
    "ANTS4-5Months3T": [
        [-56, -2, -22],  # LPA
        [1, 65, -10],  # Nasion
        [57, -1, -23],  # RPA
    ],
    "ANTS6-0Months3T": [
        [-57, -3, -24],  # LPA
        [-2, 64, -18],  # Nasion
        [55, -4, -29],  # RPA
    ],
}
# generate the MRI config files for scaling surrogate MRI to individual
# subject's digitization points. Then scale the MRI and make the BEM solution.
subject_break = False
for subject in subjects:
    if subject_break:
        break
    if subjects_to_process and subject not in subjects_to_process:
        continue
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

        # The default fiducials from the surrogate are awful. Let's fix them
        # with our manual points
        fids_path = subjects_dir / surrogate / "bem" / f"{surrogate}-fiducials.fif"
        fiducials = mne.coreg.get_mni_fiducials(surrogate, subjects_dir=subjects_dir)
        assert fiducials[0]["ident"] == FIFF.FIFFV_POINT_LPA
        assert fiducials[1]["ident"] == FIFF.FIFFV_POINT_NASION
        assert fiducials[2]["ident"] == FIFF.FIFFV_POINT_RPA
        for fi, f in enumerate(fiducials):
            f["r"] = np.array(good_fiducials[surrogate][fi]) * 1e-3
            assert f["r"].shape == (3,), f"{f['r'].shape=}"
            f["r"].setflags(write=False)
            del f, fi

        # shift the nasion
        needs_shift = (
            str(int_subj) in nasion_sub_ses and session in nasion_sub_ses[str(int_subj)]
        )
        if do_nasion_shift and needs_shift:
            nasion = fiducials[1]  # guaranteed above
            nasion["r"] = nasion["r"] + nasion_shift_xyz
            nasion["r"].setflags(write=False)
            del nasion

        raw_fname = this_subj_dir / f"{subject}_{tasks[0]}_raw.fif"
        info = mne.io.read_info(raw_fname, verbose=False)
        if not scaling_already_done:
            # run automated coreg
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
                mri_fiducials=fiducials,
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
            # make a link to the filename that MNE-BIDS-Pipeline prefers
            src_in = bem_dir / f"{subject_to}-oct-6-src.fif"
            src_out = bem_dir / f"{subject_to}-oct6-src.fif"
            assert src_in.is_file()
            hardlink(src_in, src_out, dry_run=False)

        # QC the coregistrations
        if qc:
            # load trans
            trans = mne.read_trans(
                subjects_dir / subject_to / f"{subject_to}_trans.fif"
            )
            # plot
            mne.viz.plot_alignment(
                info=info,
                trans=trans,
                subject=subject_to,
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
                + ("(Nasion shift applied)\n" if needs_shift and do_nasion_shift else "")
            )
            if response.lower().startswith("x"):
                subject_break = True
                break
            elif response.lower().startswith("c"):
                # run coregistration GUI to do it manually and compare
                ui = mne.gui.coregistration(
                    inst=raw_fname,
                    subject=surrogate,
                    subjects_dir=subjects_dir,
                    mark_inside=True,
                    block=False,
                )
                # set fiducials
                ui.coreg._setup_fiducials(fiducials)
                ui._update_distance_estimation()
                ui._update_fiducials_label()
                ui._update_fiducials()
                ui._reset(keep_trans=True)
                ui._update_fiducials()
                #from mne.viz.backends._utils import _qt_app_exec
                #_qt_app_exec(ui._renderer.figure.store["app"])
