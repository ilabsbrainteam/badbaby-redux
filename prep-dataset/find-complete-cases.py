import pandas as pd

df = pd.read_csv("qc/files-in-data.csv", header=0, index_col=0)

complete_cases = (
    df.drop(columns=["prebad", "ids", "erm"])
    .loc[df.session.isin(["a", "b"])]
    .groupby("subj")
    .all()
)
subjs = complete_cases.loc[complete_cases.mmn & complete_cases.am].index.tolist()
