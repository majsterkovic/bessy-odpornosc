"""Czynniki makro, bliznacze bessy, sezonowosc wyborow polowkowych."""
from datetime import date, timedelta

import numpy as np
import pandas as pd

BRIEF_LABELS = {
    "ropa": {1973, 1974, 1980, 1981, 1982, 1990, 2008, 2022},
    "tech": {2000, 2001, 2002, 2022},
    "wybory": {1974, 1982, 1990, 2002, 2018, 2022},
}
OIL_THRESHOLD = 0.40
TECH_THRESHOLD = 0.15


def election_day(year: int) -> date:
    d = date(year, 11, 1)
    first_monday = d + timedelta(days=(0 - d.weekday()) % 7)
    return first_monday + timedelta(days=1)


def overlaps_midterm(peak_date, trough_date) -> bool:
    return any(y % 4 == 2 for y in range(pd.Timestamp(peak_date).year, pd.Timestamp(trough_date).year + 1))


def _asof(s: pd.Series, dates) -> pd.Series:
    return pd.Series(s.asof(pd.DatetimeIndex(dates)).to_numpy(), index=pd.DatetimeIndex(dates))


def max_12m_change(s: pd.Series, start, end) -> float:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if s.index[0] > start - pd.Timedelta(days=365):
        return np.nan
    cur = s.loc[start:end]
    if cur.empty:
        return np.nan
    prior = _asof(s, cur.index - pd.Timedelta(days=365))
    return float((cur.to_numpy() / prior.to_numpy() - 1).max())


def rel_change(num: pd.Series, den: pd.Series, end, months: int = 24, tolerance_days: int = 62) -> float:
    ratio = (num / den).dropna()
    end = pd.Timestamp(end)
    begin = end - pd.DateOffset(months=months)
    if ratio.index[0] > begin + pd.Timedelta(days=tolerance_days):
        return np.nan
    start_val = ratio.asof(begin) if ratio.index[0] <= begin else ratio.iloc[0]
    return float(ratio.asof(end) / start_val - 1)


def oil_proxy(brent: pd.Series, gsci: pd.Series) -> pd.Series:
    first = brent.index[0]
    scale = brent.iloc[0] / gsci.asof(first)
    return pd.concat([gsci[gsci.index < first] * scale, brent]).sort_index()


def macro_flags(episodes: pd.DataFrame, oil: pd.Series, ixic: pd.Series, gspc: pd.Series) -> pd.DataFrame:
    out = episodes.copy()
    pk, tr = out["peak_date"], out["trough_date"]
    out["oil_12m_max"] = [max_12m_change(oil, p - pd.Timedelta(days=365), t) for p, t in zip(pk, tr)]
    out["oil_ret"] = [oil.asof(t) / oil.asof(p) - 1 if oil.index[0] <= p else np.nan for p, t in zip(pk, tr)]
    out["tech_rs_24m"] = [rel_change(ixic, gspc, p) for p in pk]
    out["midterm"] = [overlaps_midterm(p, t) for p, t in zip(pk, tr)]
    out["oil_shock"] = out["oil_12m_max"] >= OIL_THRESHOLD
    out["tech_hot"] = out["tech_rs_24m"] >= TECH_THRESHOLD
    out["n_factors"] = out[["oil_shock", "tech_hot", "midterm"]].sum(axis=1).astype(int)
    notes = []
    for _, r in out.iterrows():
        years = set(range(r.peak_date.year, r.trough_date.year + 1))
        calc = {"ropa": bool(r.oil_shock), "tech": bool(r.tech_hot), "wybory": bool(r.midterm)}
        diffs = []
        for k, lab in BRIEF_LABELS.items():
            b = bool(years & lab)
            if b != calc[k]:
                diffs.append(f"{k}: brief={'tak' if b else 'nie'}, wyliczenie={'tak' if calc[k] else 'nie'}")
        notes.append("; ".join(diffs))
    out["brief_match"] = notes
    return out


def current_state(oil: pd.Series, ixic: pd.Series, gspc: pd.Series, as_of) -> dict:
    as_of = pd.Timestamp(as_of)
    return {"oil_12m": float(oil.asof(as_of) / oil.asof(as_of - pd.Timedelta(days=365)) - 1),
            "tech_rs_24m": rel_change(ixic, gspc, as_of), "midterm": True}


def pick_twins(flags: pd.DataFrame, current: dict, k_max: int = 4, min_peak: str = "1970-01-01") -> pd.DataFrame:
    pool = flags[flags["peak_date"] >= pd.Timestamp(min_peak)].dropna(subset=["oil_12m_max", "tech_rs_24m"]).copy()
    if pool.empty:
        return pool.assign(distance=pd.Series(dtype=float))
    mo, so = pool["oil_12m_max"].mean(), pool["oil_12m_max"].std(ddof=0) or 1.0
    mt, st = pool["tech_rs_24m"].mean(), pool["tech_rs_24m"].std(ddof=0) or 1.0
    d_oil = (pool["oil_12m_max"] - current["oil_12m"]) / so
    d_tech = (pool["tech_rs_24m"] - current["tech_rs_24m"]) / st
    d_mid = pool["midterm"].astype(float) - float(current["midterm"])
    pool["distance"] = np.sqrt(d_oil ** 2 + d_tech ** 2 + d_mid ** 2)
    return pool[pool["n_factors"] >= 2].sort_values("distance").head(k_max).reset_index(drop=True)


def midterm_seasonality(gspc: pd.Series, since: int = 1950) -> tuple[pd.DataFrame, pd.DataFrame]:
    g = gspc[gspc.index >= f"{since - 1}-12-01"]
    monthly = g.resample("ME").last().pct_change().dropna()
    monthly = monthly[monthly.index.year >= since]
    is_mid = monthly.index.year % 4 == 2
    rows = []
    for m in range(1, 13):
        sel = monthly.index.month == m
        a, b = monthly[sel & is_mid], monthly[sel & ~is_mid]
        rows.append(dict(month=m, mean_wybory=a.mean(), median_wybory=a.median(), n_wybory=len(a),
                         mean_inne=b.mean(), median_inne=b.median(), n_inne=len(b)))
    post = []
    last = gspc.index[-1]
    for y in range(since, last.year + 1):
        if y % 4 != 2:
            continue
        e = pd.Timestamp(election_day(y))
        if e > last:
            post.append(dict(year=y, election_date=e, r3m=np.nan, r6m=np.nan, r12m=np.nan))
            continue
        base = gspc.asof(e)
        r = {}
        for k, mths in (("r3m", 3), ("r6m", 6), ("r12m", 12)):
            t = e + pd.DateOffset(months=mths)
            r[k] = gspc.asof(t) / base - 1 if t <= last else np.nan
        post.append(dict(year=y, election_date=e, **r))
    return pd.DataFrame(rows), pd.DataFrame(post)
