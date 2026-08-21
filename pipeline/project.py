"""Reproject to the British National Grid"""

import pandas as pd
from pyproj import Transformer

from pipeline.config import BNG, INTERIM, RAW,  WGS84

_T = Transformer.from_crs(WGS84,  BNG,  always_xy=True)

def add_bng(df):
    x, y = _T.transform(df["lng"].values, df["lat"].values)
    df  = df.copy()
    df["x"] =  x
    df["y"]  = y
    return df

def build_snap_points(thefts):
    pts = (
        thefts.groupby(["city", "lat", "lng"])
        .agg(n_thefts=("month",  "size"),
             street=("street", "first"),
             first_month=("month", "min"),
             last_month=("month", "max"))
        .reset_index()
    )
    return add_bng(pts)

def main():
    thefts =  add_bng(pd.read_csv(f"{RAW}/thefts.csv"))
    racks =  add_bng(pd.read_csv(f"{RAW}/racks.csv"))
    snaps = build_snap_points(thefts)

    thefts.to_parquet(f"{INTERIM}/thefts.parquet")
    racks.to_parquet(f"{INTERIM}/racks.parquet")
    snaps.to_parquet(f"{INTERIM}/snap_points.parquet")

    print(f"{len(thefts)} thefts at {len(snaps)} distinct snap points")
    print(f"Mean thefts per snap point: {snaps['n_thefts'].mean():.1f}")
    print(f"Max  at a  single  point: {snaps['n_thefts'].max()}")
    print("\nDistribution of thefts per snap point:")
    print(snaps["n_thefts"].value_counts().sort_index().head(15))

if  __name__ == "__main__":
    main()