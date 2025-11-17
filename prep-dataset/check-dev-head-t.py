"""Check dev_head_t for badbaby data."""

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

# TODO: Add sorted to original script, too
for data_folder in sorted(orig_data.rglob("bad_*/raw_fif/")):
    # extract the subject ID
    full_subj = data_folder.parts[-2]
    subj = full_subj.lstrip("bad_")
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
    for raw_file in data_folder.iterdir():
        if raw_file.name in bad_files:
            continue
        if "_erm_" in raw_file.name:
            continue
        # in case someone was manually trying things out:
        if "_tsss" in raw_file.name or "_pos" in raw_file.name:
            continue
        # loop over experimental tasks
        for task_code, task_name in tasks.items():
            if task_code not in raw_file.name:
                continue
            # TODO: This should move to "bidsify.py" and update metadata before writing
            refit_option = refit_options.get(raw_file.name, {})
            info = mne.io.read_info(raw_file)
            kwargs = dict(locs=False, amplitudes=False, dist_limit=0.03, linearity_limit=0.01, verbose=False)
            kwargs.update(refit_option)
            try:
                new_info = mne.chpi.refit_hpi(info.copy(), **kwargs)
            except Exception:
                print(f"Refit failed for {raw_file.name} with {refit_option=}:")
                raise
            ang, dist = mne.transforms.angle_distance_between_rigid(
                info["dev_head_t"]["trans"],
                new_info["dev_head_t"]["trans"],
                angle_units="deg",
                distance_units="mm",
            )
            print_name = raw_file.name.ljust(30)
            if ang > 20 or dist > 15:  # 20 deg or 1.5 cm
                print(
                    f"{nl}{print_name} refit delta      {ang:5.1f}° {dist:5.1f} mm"
                )
                nl = ""
            ang, dist = mne.transforms.angle_distance_between_rigid(
                info["dev_head_t"]["trans"], angle_units="deg", distance_units="mm"
            )
            if ang > 55 or dist < 20 or dist > 120:
                print(
                    f"{nl}{print_name} identity delta   {ang:5.1f}° {dist:5.1f} mm"
                )
                nl = ""
