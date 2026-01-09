"""Settings for MMN and AM data processing and analysis."""

import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, Any, Literal
from yaml import safe_load

from annotated_types import Len
from mne import Covariance
from mne_bids import BIDSPath

from mne_bids_pipeline.typing import (
    FloatArrayLike,
    PathLike,
)

# Get our task mapping strings
sys.path.insert(0, str(Path(__file__).parent.parent / "prep-dataset"))
from utils import tasks as _task_mapping
sys.path.pop(0)
_AM_str, _MMN_str = _task_mapping["am"], _task_mapping["mmn"]
del _task_mapping

# %%
# # General settings

root: PathLike = Path("/storage/badbaby-redux")
_pipeline_root: PathLike = root / "pipeline"
bids_root: PathLike | None = root / "bids-data"
subjects_dir: PathLike | None = bids_root / "derivatives" / "freesurfer" / "subjects"
sessions: list[str] | Literal["all"] = ["a", "b"]
allow_missing_sessions: bool = True
task: list[str] | str = [_AM_str, _MMN_str]
subjects: Sequence[str] | Literal["all"] = "all"
# subjects = safe_load((_pipeline_root / "subs-extra-ecg-proj.yaml").read_text("utf-8"))
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
mf_st_correlation: float = 0.95  # TODO if bandpassed first, increase to 0.98
mf_destination: Literal["reference_run", "twa"] | FloatArrayLike = "twa"
mf_int_order: int = 7
mf_mc: bool = True
mf_mc_gof_limit: float = 0.95
mf_mc_dist_limit: float = 0.01
mf_mc_rotation_velocity_limit: float | None = 30  # deg/s
mf_mc_translation_velocity_limit: float | None = 0.025  # 25 mm/s
mf_extra_kws: dict[str, Any] = dict(bad_condition="ignore")
l_freq: float | None = 0.5
h_freq: float | None = 40.0
h_trans_bandwidth: float = 5.0
# there are three peaks for 130a-noise: most prominent at 28.8, second at 29.4,
# third at 29.8, so let's put the notch filter at 29.3 and make it 5 Hz wide
# notch_freq: Sequence[float] | None = [29.3, 44.95, 60, 74.9, 104.9]
# notch_trans_bandwidth: float = 1
# notch_widths: Sequence[float] | float | None = 1.0
raw_resample_sfreq: float | None = 600

# %%
# ## Epoching

conditions = {
    _AM_str: ["amtone"],
    _MMN_str: ["standard", "deviant", "deviant/ba", "deviant/wa"],
}
epochs_decim: int = 3  # to 200 Hz
epochs_tmin: float = -0.2
epochs_tmax = {
    _AM_str: 1.7,
    _MMN_str: 1.02,  # 320 ms (stim dur) plus 700 ms (response)
}
baseline: tuple[float | None, float | None] | None = (-0.2, 0)

# %%
# Preprocessing
spatial_filter: Literal["ssp", "ica"] | None = "ssp"
n_proj_eog: dict[str, float] = dict(n_mag=0, n_grad=0, n_eeg=0)
n_proj_ecg: dict[str, float] = dict(n_mag=3, n_grad=3, n_eeg=0)
ecg_mags = safe_load((_pipeline_root / "ecg-mags.yaml").read_text("utf-8"))
ssp_ecg_channel = {k: v for k, v in ecg_mags.items() if v is not None}
del ecg_mags
reject: dict[str, float] | Literal["autoreject_global", "autoreject_local"] | None = (
    dict(grad=1500e-13, mag=3000e-15)
)

# %%
# # Sensor-level analysis

contrasts = {
    _MMN_str: [("deviant", "standard")],
}

# ## Decoding / MVPA

decoding_time_decim: int | None = 10  # 200 to 20 Hz
decoding_epochs_tmin: float | None = 0.
decoding_epochs_tmax: float | None = 0.75

# %%
# # Source-level analysis

inverse_method: Literal["MNE", "dSPM", "sLORETA", "eLORETA"] = "eLORETA"
noise_cov: (
    tuple[float | None, float | None]
    | Literal["emptyroom", "rest", "ad-hoc"]
    | Callable[[BIDSPath], Covariance]
) = "emptyroom"  # (None, 0)

# %%
# # Parallelization

n_jobs: int = 8
