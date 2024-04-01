import pandas as pd

df = pd.read_csv("files-in-data.csv", index_col=0)

with open("missing-files.txt", "w") as fid:
    for _, row in df.iterrows():
        subj = row["subj"]
        session = row["session"] if row["session"] in ("a", "b") else ""
        for kind in ("mmn", "am", "ids", "erm"):
            if not row[kind]:
                fname = f"bad_{subj}{session}_{kind}_raw.fif"
                fid.write(f"{fname}\n")
