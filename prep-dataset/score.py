import json
from ast import literal_eval
from datetime import datetime
from pathlib import Path
import re
from warnings import filterwarnings, warn
import yaml

import mne
import numpy as np
import pandas as pd
from pytz import timezone
from scipy.stats.contingency import association, crosstab

tz = "US/Pacific"  # where the recordings happened

EVENT_OFFSETS = dict(
    am=100,
    ids=200,
    mmn=300,
)

# path stuff
root = Path("/storage/badbaby-redux").resolve()
tab_dir = root / "expyfun-logs"
orig_data = root / "data"
outdir = root / "prep-dataset" / "qc"

filterwarnings(
    action="ignore",
    message="This file contains raw Internal Active Shielding data",
    category=RuntimeWarning,
    module="mne",
)
# suppress Pandas warning about concat of empty or all-NA DataFrames. The new behavior
# (keeping NAs) is what we want
filterwarnings(
    action="ignore",
    message="The behavior of DataFrame concatenation with empty or all-NA entries is",
    category=FutureWarning,
)


def parse_tab_values(value):
    """Convert string values in the TAB files to Python/NumPy types."""
    try:
        return float(value)
    except ValueError:
        if value.replace(" ", "") == "[nan]":
            return np.nan
        elif value.startswith("["):
            return literal_eval(value)[0]
        else:
            return value


def get_association(event_ids, expyfun_ids):
    """Get the association (Cramér's V) between two sequences of event codes."""
    xtab = crosstab(event_ids, expyfun_ids)
    # fake a 2D crosstab for AM-tone exp (where there's only one event)
    if xtab.count.size == 1:
        count = np.array([[xtab.count.item(), 0], [0, xtab.count.item()]])
        return association(count)
    return association(xtab.count)


def ensure_events_match(event_ids, expyfun_ids, assoc, require_ids_match=True):
    """Assert that the association is unity and the event IDs match."""
    np.testing.assert_almost_equal(assoc, 1.0, decimal=12)
    if require_ids_match:
        np.testing.assert_array_equal(event_ids, expyfun_ids)


def parse_mmn_events(raw_fname, offset=0):
    """Parse events from STIM channel for MMN experiment (which had wonky timing)."""
    raw = mne.io.read_raw_fif(raw_fname, allow_maxshield=True, preload=False)
    raw.pick("stim").load_data()
    orig_events = mne.find_events(raw, stim_channel="STI101", shortest_event=0)
    stim_idx = np.nonzero(orig_events[:, 2] == 1)[0]
    trial_ids = list()
    for ix, span in enumerate(np.array_split(orig_events, stim_idx, axis=0)):
        # all spans except the first one should start with a stim trigger (event ID 1)
        if ix == 0:
            continue
        assert span[0, 2] == 1, (ix, span)
        # because of the wonky experiment script, we expect the stim played to match the
        # trial ID *following* the stim trigger instead of the one *preceding* it
        triggers = span[:, 2]
        bit_idx = np.logical_and(triggers >= 4, triggers <= 8)
        bits = triggers[bit_idx] // 8
        if len(bits):
            trial_id = int("".join(map(str, bits)), base=2)
        else:  # final span may not have any trial ID triggers in it
            assert ix == len(stim_idx), f"bad triggers in trial {ix}/{len(stim_idx)}"
            trial_id = 0
        trial_ids.append(trial_id + offset)
    # assert np.isin(trial_ids, [2, 3, 4]).all(), np.unique(trial_ids)
    events = orig_events[stim_idx].copy()
    valid_ix = np.nonzero(trial_ids)[0]
    events[valid_ix, 2] = np.array(trial_ids)[valid_ix]
    return events[valid_ix], orig_events


def custom_extract_expyfun_events(fname, offset=0):
    """Copied from mnefun; modified to delay preloading until after stim ch picking.

    Also adds an event offset param, and removes all the button press stuff.
    """
    # Read events
    raw = mne.io.read_raw_fif(fname, allow_maxshield="yes", preload=False)
    raw.pick("stim").load_data()
    orig_events = mne.find_events(raw, stim_channel="STI101", shortest_event=0)
    events = list()
    for ch in range(1, 9):
        stim_channel = "STI%03d" % ch
        ev_101 = mne.find_events(
            raw, stim_channel="STI101", mask=2 ** (ch - 1), mask_type="and"
        )
        if stim_channel in raw.ch_names:
            ev = mne.find_events(raw, stim_channel=stim_channel)
            if not np.array_equal(ev_101[:, 0], ev[:, 0]):
                warn("Event coding mismatch between STIM channels")
        else:
            ev = ev_101
        ev[:, 2] = 2 ** (ch - 1)
        events.append(ev)
    events = np.concatenate(events)
    events = events[np.argsort(events[:, 0])]

    # check for the correct number of trials
    aud_idx = np.where(events[:, 2] == 1)[0]
    breaks = np.concatenate(([0], aud_idx, [len(events)]))
    # resps = []
    event_nums = []
    for ti in range(len(aud_idx)):
        # # pull out responses (they come *after* 1 trig)
        # these = events[breaks[ti + 1] : breaks[ti + 2], :]
        # resp = these[these[:, 2] > 8]
        # resp = np.c_[
        #     (resp[:, 0] - events[ti, 0]) / raw.info["sfreq"], np.log2(resp[:, 2]) - 3
        # ]
        # resps.append(resp if return_offsets else resp[:, 1])

        # look at trial coding, double-check trial type (pre-1 trig)
        these = events[breaks[ti + 0] : breaks[ti + 1], 2]
        serials = these[np.logical_and(these >= 4, these <= 8)]
        en = np.sum(2 ** np.arange(len(serials))[::-1] * (serials == 8)) + 1
        event_nums.append(en)

    these_events = events[aud_idx]
    these_events[:, 2] = np.array(event_nums) + offset
    # return these_events, resps, orig_events
    return these_events, orig_events


def find_matching_tabs(events, subj, session, exp_type, meas_date, logfile):
    """Convert sequences of 1,4,8 event codes into meaningful trial types."""
    rows = None
    # events from FIF (as parsed by `extract_expyfun_events`)
    event_ids = events[:, -1]
    # make sure subject and date matches in filename
    candidate_tabs = sorted(tab_dir.glob(f"{subj}_{meas_date.date()}*.tab"))
    # get the unique events from FIF
    fif_ev_uniq, fif_ev_counts = np.unique(event_ids, return_counts=True)
    fif_ev_idx = np.argsort(fif_ev_counts)
    fif_ev_uniq = fif_ev_uniq[fif_ev_idx]
    fif_ev_counts = fif_ev_counts[fif_ev_idx]
    # prepare the row data with what we already know from the FIF file
    _s = pd.StringDtype()
    _i = pd.Int64Dtype()
    _dt = pd.DatetimeTZDtype(tz=tz)
    row_with_na = pd.DataFrame(
        dict(
            subj=pd.Series([subj], dtype=_s),
            session=pd.Series([session], dtype=_s),
            exp=pd.Series([exp_type], dtype=_s),
            fif_n_events=pd.Series([event_ids.size], dtype=_i),
            tab_n_events=pd.Series([pd.NA], dtype=_i),
            fif_ev_uniq=pd.Series([fif_ev_uniq], dtype=object),
            tab_ev_uniq=pd.Series([pd.NA], dtype=object),
            fif_ev_counts=pd.Series([fif_ev_counts], dtype=object),
            tab_ev_counts=pd.Series([pd.NA], dtype=object),
            fif_time=pd.Series([meas_date], dtype=_dt),
            tab_time=pd.Series([pd.NA], dtype=_dt),
            time_diff=pd.Series([pd.NA], dtype=_s),
            tab_fname=pd.Series([pd.NA], dtype=_s),
        )
    )
    # if no TAB files found, still log something
    if not len(candidate_tabs):
        return row_with_na
    # find the correct .tab file
    tab_exp_types = list()
    for tab in candidate_tabs:
        # read the file metadata (first line of file)
        with open(tab, "r") as fid:
            header = fid.readline().lstrip("#").strip()
        # handle errant metadata
        if "runfile" in header:
            assert subj == "130"
            header = re.sub('"runfile.*\'\\)"', "'1'", header)
        metadata = json.loads(header.replace("'", '"'))
        # make sure metadata matches the experiment type we want
        match = dict(ids="ids", tone="am", syllable="mmn")
        tab_exp_type = metadata["exp_name"].lower()
        tab_exp_types.append(tab_exp_type)
        if match[tab_exp_type] != exp_type:
            continue
        assert metadata["participant"] == subj
        # find the timestamp diff between TAB file metadata and FIF `meas_date`
        pattern = "%Y-%m-%d %H_%M_%S"
        if "." in metadata["date"]:
            pattern += ".%f"
        tab_date = datetime.strptime(metadata["date"], pattern).replace(
            tzinfo=timezone(tz)
        )
        time_diff = (tab_date - meas_date).total_seconds()
        # store the time diff in a pleasant string representation
        sign = "+" if np.sign(time_diff) >= 0 else "-"
        time_diff_str = (
            f"{sign}{int(abs(time_diff)) // 3600:02d}:"  # hours
            f"{int(abs(time_diff)) // 60:02d}:"  # minutes
            f"{abs(time_diff) % 60:.3f}"  # seconds & milliseconds
        )
        # load the .tab file
        tab_df = pd.read_csv(tab, comment="#", sep="\t")
        # convert pandas-unparseable values into something intelligible
        tab_df["value"] = tab_df["value"].map(parse_tab_values)
        # convert expyfun trial_id to event code
        expyfun_ids = tab_df["value"].loc[tab_df["event"] == "trial_id"]
        if exp_type == "am":
            # all trials had same TTL ID of "2"
            expyfun_ids = np.full_like(expyfun_ids, 2, dtype=int)
        elif exp_type == "ids":
            # TTL IDs ranged from 0-4
            expyfun_ids = expyfun_ids.to_numpy().astype(int)
        elif exp_type == "mmn":
            # mapping comes from the original experiment run files (`mmn_expyfun.py`)
            trial_id_map = {
                "Dp01bw6-rms": 2,  # midpoint standard
                "Dp01bw1-rms": 3,  # ba endpoint
                "Dp01bw10-rms": 4,  # wa endpoint
            }
            expyfun_ids = expyfun_ids.map(trial_id_map).to_numpy()
        else:
            raise ValueError(f'Unrecognized experiment type "{exp_type}"')
        # offsets disambiguate the 3 experiments. Helpful but not strictly necessary
        expyfun_ids += EVENT_OFFSETS[exp_type]
        # get the unique events from TAB file
        tab_ev_uniq, tab_ev_counts = np.unique(expyfun_ids, return_counts=True)
        tab_ev_idx = np.argsort(tab_ev_counts)
        tab_ev_uniq = tab_ev_uniq[tab_ev_idx]
        tab_ev_counts = tab_ev_counts[tab_ev_idx]
        # assemble the data of interest and write it to DataFrame
        this_row = row_with_na.copy()
        this_row.update(
            dict(
                tab_n_events=[expyfun_ids.size],
                tab_ev_uniq=[tab_ev_uniq],
                tab_ev_counts=[tab_ev_counts],
                tab_time=[tab_date],
                time_diff=[time_diff_str],
                tab_fname=[tab.name],
            )
        )
        if rows is None:
            rows = this_row
        else:
            rows = pd.concat((rows, this_row), axis="index", ignore_index=True)
    # if `rows` is still None, all TAB files must have been for other experiment types
    if rows is None:
        assert exp_type not in tab_exp_types
        return row_with_na
    # if there's only one candidate TAB file, just go with it
    elif len(rows) == 1:
        return rows
    # figure out which TAB is the best match
    events_diff = rows["fif_n_events"] - rows["tab_n_events"]
    events_n_closest = abs(events_diff) == abs(events_diff).min()
    events_match = rows[["fif_ev_uniq", "tab_ev_uniq"]].apply(
        lambda row: np.array_equiv(*row), axis="columns"
    )
    # check for matching counts of each event type, allowing MMN exp to be off-by-1
    event_counts_match = rows[["fif_ev_counts", "tab_ev_counts"]].apply(
        lambda row: np.array_equiv(*row), axis="columns"
    )
    mmn_off_by_one = rows[["fif_ev_counts", "tab_ev_counts"]].apply(
        lambda row: False
        if row.iloc[0].shape != row.iloc[1].shape
        else (np.sum(np.abs(row.iloc[0] - row.iloc[1])) == 1 & (exp_type == "mmn")),
        axis="columns",
    )
    # if these three criteria are uniquely met, keep only the matching row
    _match = events_n_closest & events_match & (event_counts_match | mmn_off_by_one)
    if _match.sum() == 1:
        return rows.iloc[np.nonzero(_match)]
    # failing that, allow for event IDs to be off if the counts look good, but warn
    _match = events_n_closest & (event_counts_match | mmn_off_by_one)
    if _match.sum() == 1:
        with open(logfile, "a") as fid:
            msg = f"{subj}{session} {exp_type: >3}: event counts match but IDs don't\n"
            fid.write(msg)
        return rows.iloc[np.nonzero(_match)]
    # time_diff_series = (rows["tab_time"] - rows["fif_time"]).dt.total_seconds()
    # time_diff_shortest = abs(time_diff_series) == abs(time_diff_series).min()
    # time_diff_positive = time_diff_series > 0
    # otherwise keep all the rows, we'll want to manually decide which to keep
    return rows
