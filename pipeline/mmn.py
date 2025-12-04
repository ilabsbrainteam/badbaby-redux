"""Settings for MMN data processing and analysis."""

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, Any, Literal
from yaml import safe_load

from annotated_types import Ge, Interval, Len, MinLen
from mne import Covariance
from mne_bids import BIDSPath

from mne_bids_pipeline.typing import (
    ArbitraryContrast,
    FloatArrayLike,
    PathLike,
)

# %%
# # General settings

root: PathLike = Path("/storage/badbaby-redux")
bids_root: PathLike | None = root / "bids-data"
subjects_dir: PathLike | None = bids_root / "derivatives" / "freesurfer" / "subjects"
sessions: list[str] | Literal["all"] = ["a", "b"]
allow_missing_sessions: bool = True
task: str = "SyllableMismatchNegativity"
subjects: Sequence[str] | Literal["all"] = "all"
# with open("subs-extra-ecg-proj.yaml") as fid:
#     subjects = safe_load(fid)
exclude_subjects: Sequence[str] = [
    '232',  # session b only has `ba` deviant, not `wa` deviant
    '233',  # session b only has `ba` deviant, not `wa` deviant
]
ch_types: Annotated[Sequence[Literal["meg", "mag", "grad", "eeg"]], Len(1, 4)] = ["meg"]
data_type: Literal["meg", "eeg"] | None = "meg"
reader_extra_params: dict[str, Any] = dict(allow_maxshield="yes")
random_state: int | None = 8675309

# %%
# # Preprocessing

find_flat_channels_meg: bool = True
find_noisy_channels_meg: bool = True
find_bad_channels_extra_kws: dict[str, Any] = dict(bad_condition="ignore")
use_maxwell_filter: bool = True
mf_st_duration: float | None = 6.0  # shorter because they move a lot
mf_st_correlation: float = 0.95
mf_destination: Literal["reference_run", "twa"] | FloatArrayLike = "twa"
mf_int_order: int = 6
mf_mc: bool = True
mf_mc_gof_limit: float = 0.95
mf_mc_dist_limit: float = 0.01
mf_mc_rotation_velocity_limit: float | None = 30  # deg/s
mf_mc_translation_velocity_limit: float | None = 0.025  # 25 mm/s
mf_extra_kws: dict[str, Any] = dict(bad_condition="ignore")
l_freq: float | None = 0.1
h_freq: float | None = 50.0
raw_resample_sfreq: float | None = 600

# %%
# ## Epoching

conditions: Sequence[str] | dict[str, str] | None = ["standard", "deviant", "deviant/ba", "deviant/wa"]
epochs_tmin: float = -0.2
epochs_tmax: float = 1.02  # 320 ms (stim dur) plus 700 ms (response)
baseline: tuple[float | None, float | None] | None = (-0.2, 0)
spatial_filter: Literal["ssp", "ica"] | None = "ssp"
n_proj_eog: dict[str, float] = dict(n_mag=0, n_grad=0, n_eeg=0)
n_proj_ecg: dict[str, float] = dict(n_mag=3, n_grad=3, n_eeg=0)
with open("ecg-mags.yaml") as fid:
    ecg_mags = safe_load(fid)
ssp_ecg_channel = {k: v for k, v in ecg_mags.items() if v is not None}
del ecg_mags, fid
reject: dict[str, float] | Literal["autoreject_global", "autoreject_local"] | None = (
    dict(grad=1500e-13, mag=6000e-15)
)

# %%
# # Sensor-level analysis

contrasts: Sequence[tuple[str, str] | ArbitraryContrast] = [("deviant", "standard")]

# ## Decoding / MVPA

decode: bool = False
decoding_epochs_tmin: float | None = 0.
decoding_epochs_tmax: float | None = 0.75

# %%
# # Source-level analysis

recreate_bem: bool = True
spacing: Literal["oct5", "oct6", "ico4", "ico5", "all"] | int = "ico4"
inverse_method: Literal["MNE", "dSPM", "sLORETA", "eLORETA"] = "eLORETA"
noise_cov: (
    tuple[float | None, float | None]
    | Literal["emptyroom", "rest", "ad-hoc"]
    | Callable[[BIDSPath], Covariance]
) = "emptyroom"  # (None, 0)

# %%
# # Parallelization

n_jobs: int = 8
