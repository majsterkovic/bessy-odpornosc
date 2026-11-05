"""Wyznaczanie bess i korekt indeksu (zygzak)."""
import numpy as np
import pandas as pd

COLUMNS = ["episode_id", "peak_date", "peak", "trough_date", "trough", "depth", "days_to_trough",
           "recovery_date", "days_to_recovery", "kind", "confirmed"]


def find_episodes(close: pd.Series, decline: float = 0.15, rebound: float = 0.30) -> pd.DataFrame:
    v = close.to_numpy(float)
    idx = close.index
    rows = []
    peak_i = 0
    trough_i = None  # None = stan "wzrost"

    def emit(p, t, confirmed):
        after = np.nonzero(v[t:] >= v[p])[0]
        rec = idx[t + after[0]] if len(after) else pd.NaT
        depth = v[t] / v[p] - 1
        rows.append(dict(
            episode_id=idx[p].strftime("%Y-%m-%d"), peak_date=idx[p], peak=v[p],
            trough_date=idx[t], trough=v[t], depth=depth, days_to_trough=(idx[t] - idx[p]).days,
            recovery_date=rec, days_to_recovery=(rec - idx[t]).days if pd.notna(rec) else np.nan,
            kind="bessa" if depth <= -0.20 + 1e-9 else "korekta", confirmed=confirmed))

    for i in range(1, len(v)):
        if trough_i is None:
            if v[i] > v[peak_i]:
                peak_i = i
            elif v[i] <= v[peak_i] * (1 - decline):
                trough_i = i
        else:
            if v[i] < v[trough_i]:
                trough_i = i
            elif v[i] >= v[trough_i] * (1 + rebound) or v[i] >= v[peak_i]:
                emit(peak_i, trough_i, True)
                peak_i, trough_i = i, None
    if trough_i is not None:
        emit(peak_i, trough_i, False)
    return pd.DataFrame(rows, columns=COLUMNS)
