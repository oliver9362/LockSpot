import numpy as np
import pandas as pd

from pipeline.config import INTERIM

RNG = np.random.default_rng(42)

def fit_lookup(racks):
    """Median capactiy by parking type from racks that are tagged"""
    tagged = racks[racks["capacity"].notna()]
    by_type = tagged.groupby("parking_type")["capacity"].agg(["median", "size"])
    by_type = by_type[by_type["size"] >= 5]
    return by_type["median"].to_dict(), tagged["capacity"].median()

def apply_lookup(racks, lookup, fallback):
    out = racks.copy()
    imputed = out["parking_type"].map(lookup).fillna(fallback)
    out["capacity_imputed"] = out["capacity"].isna()
    out["capacity_final"] = out["capacity"].fillna(imputed)
    return out

def validate(racks, n_folds=5):
    tagged = racks[racks["capacity"].notna()].copy()
    idx = RNG.permutation(len(tagged))
    folds = np.array_split(idx, n_folds)

    errors = []
    for fold in folds:
        mask = np.zeros(len(tagged), dtype=bool)
        mask[fold] = True
        train, test = tagged[~mask], tagged[mask]

        lookup, fallback = fit_lookup(train)
        pred = test["parking_type"].map(lookup).fillna(fallback)
        errors.extend((pred.values - test["capacity"].values).tolist())

    errors = np.array(errors)
    return {
        "mae": float(np.abs(errors).mean()),
        "median_ae":  float(np.median(np.abs(errors))),
        "n": int(len(errors)),
        "baseline_mae": float(
            np.abs(tagged["capacity"] - tagged["capacity"].median()).mean()
        ),
    }

def main():
    racks = pd.read_parquet(f"{INTERIM}/racks.parquet")

    stats = validate(racks)
    print("Cross-validated imputation error")
    print(f"  MAE:              {stats['mae']:.2f} spaces")
    print(f"  Median abs error: {stats['median_ae']:.2f} spaces")
    print(f"  Baseline (global median): {stats['baseline_mae']:.2f} spaces")
    print(f"  Tested on {stats['n']} tagged racks")

    lookup, fallback = fit_lookup(racks)
    out = apply_lookup(racks, lookup, fallback)
    out.to_parquet(f"{INTERIM}/racks_capacity.parquet")

    print(f"\nImputed {out['capacity_imputed'].sum()} of {len(out)} racks")
    print(f"Total spaces in study area: {out['capacity_final'].sum():.0f}")

if __name__ == "__main__":
    main()