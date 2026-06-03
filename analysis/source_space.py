"""Run source-space analysis of data.

|        |         2 mo        |         6 mo        |
+--------+---------------------+---------------------+
|        | speech | non-speech | speech | non-speech |
| PMC-lh |        |            |        |            |
|    -rh |        |            |        |            |
| IFG-lh |        |            |        |            |
|    -rh |        |            |        |            |
| AAC-lh |        |            |        |            |
|    -rh |        |            |        |            |

Done:
- Make sure all files are present
- Generate labelized data
- Tried eLORETA
- Create plots:
  - 2 ages: 2mo, 6mo
  - 3 ROIs (Glasser 2016): Precentral gyrus (PCG), Inferior frontal gyrus (IFG), auditory (STG)
  - 4 traces: standard, deviant/ba, deviant (ba+wa), am
  - Time windows: 2mo=(200-375), 6mo=(150-250)

TODO:
- Maybe should use mean_flip instead of vector?
- Use VectorSourceEstimate.project to project onto the normals?
- Measure:
  - (S-M)/sqrt(S*M)
- Create concat epochs baseline cov, use that
- Look into incomplete subjects (bad_subjects below)
- Look into Alexis event counts: 232 and 233 there are no counts for deviant wa at 6mo, 232 only AM at 2mo
"""
import json
import sys
from pathlib import Path

import h5io
import numpy as np
import mne
import matplotlib.pyplot as plt
from tqdm import tqdm

sys.path.append(str(Path(__file__).parents[1] / "pipeline"))

import config

# Params
conditions = config.conditions
tasks = tuple(config.task)
assert tasks == tuple(conditions)
all_conditions = tuple(sum(conditions.values(), []))
sessions = tuple(f"ses-{s}" for s in config.sessions)
assert len(sessions) == 2, sessions
tmax = min(config.epochs_tmax.values())  # could use (-0.1, 0.7) for equiv with orig
tmin = config.epochs_tmin
assert tmin == -0.2, tmin
rois = (
    "Premotor Cortex",  # Precentral gyrus
    "Inferior Frontal Cortex",  # Inferior frontal gyrus
    "Auditory Association Cortex",  # Superior temporal gyrus
)
hemis = ("lh", "rh")
label_names = tuple(
    f"{name}-{hemi}"
    for name in rois
    for hemi in hemis
)
sfreq = config.raw_resample_sfreq / config.epochs_decim
assert sfreq == 200.
times = np.arange(int(round((tmax - tmin) * sfreq)) + 1) / sfreq + tmin
method = "eLORETA"  # or dSPM, etc.
del rois, config

# Paths
this_dir = Path(__file__).parent
root_dir = this_dir.parent
deriv_path = root_dir / "bids-data" / "derivatives"
subjects_dir = deriv_path / "freesurfer" / "subjects"
data_path = deriv_path / "mne-bids-pipeline"
label_dir = this_dir / "label_data"
label_dir.mkdir(exist_ok=True)
mne.datasets.fetch_fsaverage(subjects_dir=subjects_dir)
mne.datasets.fetch_aparc_sub_parcellation(subjects_dir=subjects_dir)

parc = "HCPMMP1_combined"
labels = mne.read_labels_from_annot(
    "fsaverage", parc=parc, subjects_dir=subjects_dir
)
found_names = [label.name for label in labels]
labels = tuple(labels[found_names.index(label_name)] for label_name in label_names)
fsaverage_src = mne.read_source_spaces(
    subjects_dir / "fsaverage" / "bem" / "fsaverage-ico-5-src.fif"
)
del found_names, parc

bad_subjects = (
    # missing ses-b
    "sub-123",
    "sub-125",
    "sub-126",
    "sub-132",
    "sub-218",
    "sub-222",
    "sub-228",
    "sub-302",
    "sub-307",
    "sub-316",
    # missing ses-a
    "sub-317",
    "sub-318",
    "sub-320",
    # no counts for deviant wa at 6mo, but also not rsync'ed
    # "sub-232",
    # "sub-233",
)
subjects = sorted(path.name for path in data_path.glob("sub-*"))
for bad_subject in bad_subjects:
    subjects.pop(subjects.index(bad_subject))
subjects = tuple(subjects)
assert len(subjects) == 38 - len(bad_subjects), len(subjects)
subjects_sessions = tuple(
    (subject, session)
    for subject in subjects
    for session in sessions
)
for ssi, (subject, session) in enumerate(tqdm(
    subjects_sessions, desc="subject/session", miniters=1, mininterval=0.0
)):
    # Figure out if we need to regenerate label data
    subj_sess = f"{subject}_{session}"
    label_path = label_dir / f"{subj_sess}_label_data_{method}.h5"
    if label_path.is_file():
        continue
    deriv_root = data_path / f"{subject}" / f"{session}" / "meg"
    del subject, session
    cov_path = deriv_root / f"{subj_sess}_task-noise_proc-clean_cov.fif"
    cov = mne.read_cov(cov_path)
    fwd_path = deriv_root / f"{subj_sess}_fwd.fif"
    fwd = mne.read_forward_solution(fwd_path)
    rank_path = deriv_root / f"{subj_sess}_task-noise_proc-clean_rank.json"
    rank = json.loads(rank_path.read_text("utf-8"))
    # Though maybe we want concat epochs baseline cov?
    all_epochs = list()
    for task in tasks:
        epochs_path = deriv_root / f"{subj_sess}_task-{task}_proc-clean_epo.fif"
        all_epochs.append(mne.read_epochs(epochs_path, preload=True))
        all_epochs[-1].crop(tmin=None, tmax=tmax)
    epochs = mne.concatenate_epochs(  # ignore dropped annots
        all_epochs, verbose="error",
    )
    assert np.allclose(times, epochs.times)
    del all_epochs
    inv = mne.minimum_norm.make_inverse_operator(
        epochs.info, fwd, cov, rank=rank, loose=0.2,
    )
    # Apply, morph, extract
    info = epochs.average().info
    label_op_evoked = mne.EvokedArray(np.eye(info["nchan"]), info)
    stc = mne.minimum_norm.apply_inverse(
        label_op_evoked, inv, lambda2=1.0 / 9.0, method=method, pick_ori="vector",
    )
    fs_subject = fwd["src"][0]["subject_his_id"]
    morph = mne.compute_source_morph(  # we know we miss a few verts
        fwd["src"], subjects_dir=subjects_dir, smooth=10, verbose="error",
    )
    stc_fsaverage = morph.apply(stc)
    label_op = mne.extract_label_time_course(
        stc_fsaverage, list(labels), src=fsaverage_src, mode="mean"
    )
    assert label_op.shape == (len(label_names), 3, info["nchan"]), label_op.shape
    # Apply to each condition
    label_data_out = dict(
        label_names=tuple(label.name for label in labels),
        all_conditions=all_conditions,
        tmin=epochs.tmin,
        sfreq=epochs.info["sfreq"],
        nave=np.zeros(len(all_conditions), dtype=int),
        data=np.zeros((len(all_conditions), len(label_names), 3, len(times))),
    )
    for ci, condition in enumerate(all_conditions):
        these_epochs = epochs[condition]
        assert len(these_epochs) > 10, len(these_epochs)
        ave = these_epochs.average()
        label_data_out["nave"][ci] = ave.nave
        label_data_out["data"][ci] = label_op @ ave.data
    h5io.write_hdf5(label_path, label_data_out)

# Load all data
all_data = np.zeros(
    (len(subjects), len(sessions), len(all_conditions), len(labels), 3, len(times))
)
all_nave = np.zeros((len(subjects), len(sessions), len(all_conditions)), dtype=int)
for ssi, (subject, session) in enumerate(subjects_sessions):
    label_path = label_dir / f"{subject}_{session}_label_data_{method}.h5"
    this_label_data = h5io.read_hdf5(label_path)
    data = this_label_data["data"]
    assert this_label_data["label_names"] == label_names
    assert this_label_data["all_conditions"] == all_conditions
    assert np.isclose(this_label_data["tmin"], tmin)
    assert np.isclose(this_label_data["sfreq"], sfreq)
    ri, ci = divmod(ssi, len(sessions))
    all_data[ri, ci] = data
    all_nave[ri, ci] = this_label_data["nave"]

# Do the plotting
n_row = len(label_names)
n_col = len(sessions) * len(tasks)
fig, axes = plt.subplots(
    n_row, n_col, figsize=(n_col * 2, n_row * 2), sharex=True,
    layout="constrained",
)
task_colors = {
    "amtone": "tab:blue",
    "standard": "k",
    "deviant": "tab:red",
    "deviant/ba": "tab:orange",
    "deviant/wa": "tab:purple",
}
session_titles = {
    "ses-a": "2 mo",
    "ses-b": "6 mo",
}
task_titles = {
    "AMTone": "Non-speech",
    "SylMMN": "Speech",
}
# subj, ses, cond, label, 3, time
sessions_tasks = tuple(  # col level 1 (2mo, 6mo) and 2 (SylMM, AM)
    (session, task)
    for session in sessions
    for task in tasks[::-1]  # plot in other order
)
regions = {
    "ses-a": (0.2, 0.375),
    "ses-b": (0.15, 0.25),
}
shareys = {}
for ci, (session, task) in enumerate(sessions_tasks):
    for li, label_name in enumerate(label_names):  # row level (ROI)
        ax = axes[li, ci]
        share_key = (session,)
        if share_key not in shareys:
            shareys[share_key] = ax
        else:
            ax.sharey(shareys[share_key])
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for cond in conditions[task]:  # trace level (task)
            cond_idx = all_conditions.index(cond)
            data = np.linalg.norm(
                all_data[:, sessions.index(session), cond_idx, li, :, :],
                axis=-2,  # vector norm across directions
            )
            # rescale using nave
            # data *= np.sqrt(all_nave[:, sessions.index(session), cond_idx][:, np.newaxis])
            mean = np.mean(data, axis=0)
            sem = np.std(data, axis=0) / np.sqrt(data.shape[0])
            color = task_colors[cond]
            ax.plot(times, mean.T, linewidth=1, zorder=4, color=color, label=cond)
            ax.fill_between(times, (mean - sem).T, (mean + sem).T, alpha=0.3, zorder=3, facecolor=color, edgecolor="none")
        sps = ax.get_subplotspec()
        if sps.is_first_row():
            ax.set_title(f"{session_titles[session]}\n{task_titles[task]}")
        if sps.is_first_col():
            if label_name.endswith(hemis[0]):
                ylabel = label_name.replace("-", " ").replace(" ", "\n")[:-2] + "LH"
            else:
                assert label_name.endswith(hemis[1])
                ylabel = (label_name.count(" ") + 1) * "\n" + "RH"
            ax.set_ylabel(ylabel)
        if sps.is_last_row():
            ax.set_xlabel("Time (s)")
        if sps.is_first_row() and ci in (0, 1):
            ax.legend(loc="upper right", fontsize="xx-small")
        ax.set_xlim(times[0], times[-1])
        ax.axvspan(*regions[session], color="tab:green", alpha=0.1, zorder=1)
