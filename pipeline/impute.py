import numpy as np
import pandas as pd

from pipeline.config import INTERIM

RNG = np.random.default_rng(42)

def fit_lookup(racks):
    """Median capactiy by parking type from racks that are tagged"""
    tagged = racks[racks["capacity"].notna()].copy()
    tagged["is_way"] = tagged["osm_id"].str.startswith("way/")

    by_key = (tagged.groupby(["parking_type", "is_way"])["capacity"]
              .agg(["median", "size"]))
    by_key = by_key[by_key["size"] >= 5]

    return by_key["median"].to_dict(), tagged["capacity"].median()

def apply_lookup(racks, lookup, fallback):
    out = racks.copy()
    out["is_way"] = out["osm_id"].str.startswith("way/")

    keys = zip(out["parking_type"], out["is_way"])
    imputed = pd.Series([lookup.get(k, fallback) for k in keys], index=out.index)

    out["capacity_imputed"] = out["capacity"].isna()
    out["capacity_final"] = out["capacity"].fillna(imputed)
    return out

def validate(racks, n_folds=5):
    tagged = racks[racks["capacity"].notna()].copy()
    idx = RNG.permutation(len(tagged))
    folds = np.array_split(idx, n_folds)

    errors, log_errors = [], []
    base_log_errors = []
    global_median = tagged["capacity"].median()

    for fold in folds:
        mask = np.zeros(len(tagged), dtype=bool)
        mask[fold] = True
        train, test = tagged[~mask], tagged[mask]

        lookup, fallback = fit_lookup(train)
        pred = apply_lookup(test, lookup, fallback)["capacity_final"]

        # apply_lookup keeps real values where present, so for a fold whose
        # capacities are all known we must impute deliberately instead.
        keys = zip(test["parking_type"],
                   test["osm_id"].str.startswith("way/"))
        pred = np.array([lookup.get(k, fallback) for k in keys])
        actual = test["capacity"].values

        errors.extend((pred - actual).tolist())

        ok = (pred > 0) & (actual > 0)
        log_errors.extend(np.abs(np.log(pred[ok]) - np.log(actual[ok])).tolist())
        base_log_errors.extend(
            np.abs(np.log(global_median) - np.log(actual[ok])).tolist())

    errors = np.array(errors)
    log_errors = np.array(log_errors)
    base_log_errors = np.array(base_log_errors)

    return {
        "mae": float(np.abs(errors).mean()),
        "median_ae": float(np.median(np.abs(errors))),
        "mae_log": float(log_errors.mean()),
        "factor": float(np.exp(log_errors.mean())),
        "baseline_mae": float(np.abs(actual_all_baseline(tagged)).mean()),
        "baseline_log": float(base_log_errors.mean()),
        "baseline_factor": float(np.exp(base_log_errors.mean())),
        "n": int(len(errors)),
    }


def actual_all_baseline(tagged):
    return tagged["capacity"] - tagged["capacity"].median()

def main():
    racks = pd.read_parquet(f"{INTERIM}/racks.parquet")

    stats = validate(racks)
    print("Cross-validated imputation error")
    print(f"  MAE:                 {stats['mae']:.2f} spaces")
    print(f"  Median abs error:    {stats['median_ae']:.2f} spaces")
    print(f"  Baseline MAE:        {stats['baseline_mae']:.2f} spaces")
    print()
    print(f"  Log error:           {stats['mae_log']:.3f} "
          f"(typically off by {stats['factor']:.2f}x)")
    print(f"  Baseline log error:  {stats['baseline_log']:.3f} "
          f"(typically off by {stats['baseline_factor']:.2f}x)")
    print(f"  Tested on {stats['n']} tagged racks")

    lookup, fallback = fit_lookup(racks)
    out = apply_lookup(racks, lookup, fallback)
    out.to_parquet(f"{INTERIM}/racks_capacity.parquet")

    print(f"\nImputed {out['capacity_imputed'].sum()} of {len(out)} racks")
    print(f"Total spaces in study area: {out['capacity_final'].sum():.0f}")

if __name__ == "__main__":
    main()