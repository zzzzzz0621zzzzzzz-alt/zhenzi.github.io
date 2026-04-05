from __future__ import annotations

from pathlib import Path

import pandas as pd


INPUT_CSV = Path("/Users/czh/Documents/SYSU/数理统计课/WVS_Cross-National_Wave_7_csv_v6_0.csv")
OUTPUT_CSV = Path("/Users/czh/Documents/SYSU/数理统计课/WVS_Wave_7_with_normalized_vars.csv")


def normalize_series(
    series: pd.Series,
    *,
    valid_min: float,
    valid_max: float,
    reverse: bool = False,
) -> pd.Series:
    """Min-max normalize a series to [0, 1].

    WVS often uses negative values such as -1/-2/-4/-5 for missing codes,
    so those values are excluded before normalization.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.where((numeric >= valid_min) & (numeric <= valid_max))

    normalized = (valid - valid_min) / (valid_max - valid_min)
    if reverse:
        normalized = 1 - normalized

    return normalized


def add_normalized_variable(
    df: pd.DataFrame,
    *,
    source_col: str,
    target_name: str,
    valid_min: float,
    valid_max: float,
    reverse: bool = False,
) -> pd.DataFrame:
    """Create two new variables: one readable alias and one `-nrm` version."""
    result = df.copy()
    result[target_name] = pd.to_numeric(result[source_col], errors="coerce")
    result[f"{target_name}-nrm"] = normalize_series(
        result[source_col],
        valid_min=valid_min,
        valid_max=valid_max,
        reverse=reverse,
    )
    return result


def main() -> None:
    df = pd.read_csv(INPUT_CSV)

    # Q46 is the Wave 7 happiness item. Lower values mean happier,
    # so we reverse the normalized score to make higher = happier.
    df = add_normalized_variable(
        df,
        source_col="Q46",
        target_name="happy",
        valid_min=1,
        valid_max=4,
        reverse=True,
    )

    df.to_csv(OUTPUT_CSV, index=False)

    preview = df.loc[:, ["Q46", "happy", "happy-nrm"]].head(10)
    print(f"Saved: {OUTPUT_CSV}")
    print(preview.to_string(index=False))


if __name__ == "__main__":
    main()
