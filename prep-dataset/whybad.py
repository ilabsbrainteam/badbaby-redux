"""Document and check our assumptions about why subjects are bad."""

from pathlib import Path

known_bads = {}
n_am = set("120 129 208 229 232".split())
no_mmn = set("215 227 305 308 312 315".split())

root = Path("/storage/badbaby-redux").resolve()
orig_data = root / "data"
all_subjects = [
    data_folder.parts[-2].lstrip("bad_")
    for data_folder in sorted(orig_data.rglob("bad_*/raw_fif/"))
]
all_subjects = set(
    subj[:-1] for subj in all_subjects
    if subj.endswith("a")
    and f"{subj[:-1]}b" in all_subjects
)
print(f"Starting with {len(all_subjects)} paired subjects that we have data for")
assert no_mmn.isdisjoint(n_am), "Some subjects are in both AM and MMN bad lists"
lost_am = all_subjects.intersection(n_am)
print(f"Subjects with no AM: {lost_am}")
print(f"Subjects with no MMN: {all_subjects.intersection(no_mmn)}")
print(f"Total expected usable subjects: {len(all_subjects - lost_am - no_mmn)}:\n{sorted(all_subjects - lost_am - no_mmn)}")

# Iterate through all reports and make sure that there are ECGs (the problem with 319a)
report_dir = Path(__file__).parents[1] / "reports" / "2026-04-20"
assert report_dir.is_dir(), f"Expected {report_dir} to exist"
report_paths = sorted(path for path in report_dir.rglob("sub-*_ses-*_report.html") if "sub-average" not in path.name)
# assert len(report_paths) == len(all_subjects) * 2, f"{len(report_paths)=} != {len(all_subjects) * 2=}"
bad = []
for report_path in report_paths:
    report_text = report_path.read_text("utf-8")
    if "SSP: ECG" not in report_text:
        bad.append(report_path.parts[-1].split("_report.html")[0])
if bad:
    print(f"Subjects with missing ECGs:\n{'\n'.join(bad)}")
