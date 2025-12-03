"""Check dev_head_t for badbaby data.

After running this function, prep-dataset/dev-head-t-report.html will be created.
Manually inspect this file, and decide which refits should actually be used during
bidsify.py. Set ``refit: True`` for those subjects in prep-dataset/refit-options.yml.
"""

from pathlib import Path
import mne
import yaml

root = Path("/storage/badbaby-redux").resolve()
orig_data = root / "data"
outdir = root / "prep-dataset" / "qc"
with open(outdir.parent / "bad-files.yaml", "r") as fid:
    bad_files = yaml.load(fid, Loader=yaml.SafeLoader)
# tasks
tasks = dict(
    am="AmplitudeModulatedTones",
    ids="InfantDirectedSpeech",
    mmn="SyllableMismatchNegativity",
)
with open(outdir.parent / "refit-options.yml", "r") as fid:
    refit_options = yaml.load(fid, Loader=yaml.SafeLoader)
report_file = outdir / "dev-head-t-report.h5"
subjects_dir = root / "anat"
check_runs = set("bad_317a_mmn_raw.fif".split())

data_folders = sorted(orig_data.rglob("bad_*/raw_fif/"))
all_files = set(sum((list(file.name for file in data_folder.iterdir()) for data_folder in data_folders), []))
missing = set(refit_options) - set(all_files)
assert missing == set(), f"refit-options.yml has subjects not in all_files: {missing}"
for data_folder in data_folders:
    # extract the subject ID
    subject = data_folder.parts[-2]
    subj = subject.lstrip("bad_")
    if subj.endswith("a"):
        session = "a"
    elif subj.endswith("b"):
        session = "b"
    else:
        session = "c"
    # BIDS requires subj to be a string, but cast to int as a failsafe first
    subj = str(int(subj[:3]))
    erm_files = list(data_folder.glob("*_erm_raw.fif"))
    nl = "\n"
    for raw_file in sorted(data_folder.iterdir()):
        if raw_file.name in bad_files:
            continue
        if "_erm_" in raw_file.name:
            continue
        # in case someone was manually trying things out:
        if "_tsss" in raw_file.name or "_pos" in raw_file.name:
            continue
        if check_runs and raw_file.name not in check_runs:
            continue
        task = [task_code for task_code in tasks if task_code in raw_file.name]
        assert len(task) in (0, 1), len(task)
        if not len(task):
            continue
        task = task[0]
        refit_option = refit_options.get(raw_file.name, {}).copy()
        refit_option.pop("refit", None)  # remove 'refit' key if present
        info = mne.io.read_info(raw_file)
        verbose = raw_file.name in check_runs
        if verbose:
            print(raw_file.name)
        kwargs = dict(locs=False, amplitudes=False, dist_limit=0.01, colinearity_limit=0.01, verbose=verbose)
        kwargs.update(refit_option)
        try:
            new_info = mne.chpi.refit_hpi(info.copy(), **kwargs)
        except Exception:
            print(f"Refit failed for {raw_file.name} with {refit_option=}:")
            raise
        ang_d, dist_d = mne.transforms.angle_distance_between_rigid(
            info["dev_head_t"]["trans"],
            new_info["dev_head_t"]["trans"],
            angle_units="deg",
            distance_units="mm",
        )
        print_name = raw_file.name.ljust(30)
        why = list()
        if ang_d > 20 or dist_d > 15:  # 20 deg or 1.5 cm
            why.append(f"refit delta      {ang_d:5.1f}° {dist_d:5.1f} mm")
            print(f"{nl}{print_name} {why[-1]}")
            nl = ""
        ang_i, dist_i = mne.transforms.angle_distance_between_rigid(
            info["dev_head_t"]["trans"], angle_units="deg", distance_units="mm"
        )
        if ang_i > 65 or dist_i < 20 or dist_i > 120:
            why.append(f"identity delta   {ang_i:5.1f}° {dist_i:5.1f} mm")
            print(f"{nl}{print_name} {why[-1]}")
            nl = ""
        if why:
            if verbose:
                input("Press Enter to continue...")
            # Generate report figures
            figs = list()
            try:
                trans = mne.read_trans(
                    subjects_dir / f"{subject}_{task}" / f"{subject}_{task}_trans.fif"
                )
            # ...if it doesn't exist, the non-task-specific is the correct one
            except FileNotFoundError:
                trans = mne.read_trans(subjects_dir / subject / f"{subject}_trans.fif")
                plot_subject = subject
            else:
                plot_subject = f"{subject}_{task}"
            for this_info in (info, new_info):
                fig = mne.viz.create_3d_figure(bgcolor="w", size=(800, 800))
                mne.viz.plot_alignment(this_info, trans, subject=plot_subject, subjects_dir=subjects_dir, coord_frame="meg", fig=fig, dig=True)
                figs.append(fig)
            with mne.report.open_report(report_file, title="check-dev-head-t report") as report:
                report.add_html(
                    "<br>".join(why), title=f"{print_name} info", section=subject, replace=True,
                )
                report.add_figure(
                    figs, title=f"{print_name} alignment", section=subject, replace=True,
                )
                report.save(report_file.with_suffix(".html"), overwrite=True, open_browser=False)
            for fig in figs:
                mne.viz.close_3d_figure(fig)
