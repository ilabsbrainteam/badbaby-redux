from pathlib import Path

import mne

bids_root = Path("/storage/badbaby-redux/bids-data")
deriv_root = bids_root / "derivatives" / "mne-bids-pipeline"
fpaths = deriv_root.rglob("**/sub-*_ses-?_task-AmplitudeModulatedTones_epo.fif")


def drop_epochs_with_short_isi(epochs: mne.Epochs, event: str) -> mne.Epochs:
    """Add metadata regarding the relative timing of prior / next trials."""
    kwargs = dict(
        events=epochs.events, event_id=epochs.event_id, sfreq=epochs.info["sfreq"]
    )
    # we have to do this twice, once for pre-stim times and once for post-stim times,
    # due to the limitation of `make_metadata` of only keeping one `amtone` event per
    # epoch window. Thus `tmin`, `tmax`, and `keep_(first|last)` differ here:
    metadata_bef, ev_bef, evid_bef = mne.epochs.make_metadata(
        tmin=-1.7, tmax=0, keep_first=event, **kwargs
    )
    metadata_aft, ev_aft, evid_aft = mne.epochs.make_metadata(
        tmin=0.0, tmax=1.7, keep_last=event, **kwargs
    )
    drop_bef = metadata_bef.loc[metadata_bef[event] < 0]
    drop_aft = metadata_aft.loc[metadata_aft[event] > 0]
    drop_ix = sorted(set(drop_bef.index) | set(drop_aft.index))
    epochs.drop(drop_ix)

    return epochs


for fpath in fpaths:
    epo = mne.read_epochs(fpath)
    backup_name = fpath.with_name(fpath.name.replace("_epo.fif", "_no-dropped-epo.fif"))
    fpath.rename(backup_name)
    epo = drop_epochs_with_short_isi(epo, "amtone")
    epo.save(fpath)
