"""Wycena P/E spolek i sektorow (EPS z SEC, na dzisiejszej bazie akcji)."""
import numpy as np
import pandas as pd

TTM_SPAN_DAYS = 300
LATEST_QUARTER_MAX_AGE = 270


def split_factor(date, splits: pd.DataFrame | None) -> float:
    """Iloczyn wspolczynnikow splitow z ex_date po `date` (nowe/stare akcje)."""
    if splits is None or splits.empty:
        return 1.0
    later = splits.loc[splits["ex_date"] > pd.Timestamp(date), "ratio"]
    return float(np.prod(later.astype(float))) if len(later) else 1.0


def quarterly_eps(rows: pd.DataFrame, splits: pd.DataFrame | None = None) -> pd.DataFrame:
    """Kwartalny EPS jednej spolki: period_end, eps, usable_from. Q4 = rok - Q1 - Q2 - Q3 (gdy brak wiersza Q4).

    Kazda wartosc jest dzielona przez splity po jej dacie publikacji, zeby wszystko lezalo na dzisiejszej bazie akcji.
    """
    r = rows.copy()
    r["period_end"] = pd.to_datetime(r["period_end"])
    r["usable_from"] = pd.to_datetime(r["usable_from"])
    r["eps"] = [v / split_factor(u, splits) for v, u in zip(r["value"].astype(float), r["usable_from"])]
    quarters = r[r["period_type"] == "quarterly"][["period_end", "eps", "usable_from"]]
    derived = []
    for _, a in r[r["period_type"] == "annual"].iterrows():
        e = a["period_end"]
        if ((quarters["period_end"] - e).abs() <= pd.Timedelta(days=10)).any():
            continue
        inside = quarters[(quarters["period_end"] > e - pd.Timedelta(days=300)) &
                          (quarters["period_end"] <= e - pd.Timedelta(days=60))]
        if len(inside) == 3:
            derived.append(dict(period_end=e, eps=a["eps"] - inside["eps"].sum(), usable_from=a["usable_from"]))
    out = pd.concat([quarters, pd.DataFrame(derived, columns=quarters.columns)], ignore_index=True)
    out["period_end"] = pd.to_datetime(out["period_end"])
    out["usable_from"] = pd.to_datetime(out["usable_from"])
    out["eps"] = out["eps"].astype(float)
    return out.sort_values("period_end").reset_index(drop=True)


def ttm_eps(q: pd.DataFrame, as_of) -> float:
    as_of = pd.Timestamp(as_of)
    usable = q[q["usable_from"] <= as_of].tail(4)
    if len(usable) < 4:
        return np.nan
    pe = usable["period_end"]
    if (pe.iloc[-1] - pe.iloc[0]).days > TTM_SPAN_DAYS or (as_of - pe.iloc[-1]).days > LATEST_QUARTER_MAX_AGE:
        return np.nan
    return float(usable["eps"].sum())


def pe_monthly(px_month_end: pd.Series, q: pd.DataFrame, splits: pd.DataFrame | None = None) -> pd.Series:
    """P/E na koniec miesiaca z surowej ceny zamkniecia; NaN gdy brak TTM albo EPS TTM <= 0."""
    out = []
    for d, px in px_month_end.items():
        eps = ttm_eps(q, d)
        adj_px = px / split_factor(d, splits)
        out.append(adj_px / eps if eps and eps > 0 else np.nan)
    return pd.Series(out, index=px_month_end.index)


def pe_filter(current_pe: float, history: pd.Series, min_months: int = 60,
              eps_ttm: float | None = None) -> tuple[bool, str, float]:
    """(przechodzi, powod, percentyl P/E w swojej historii).

    Odrzuca: ujemny/zerowy EPS TTM oraz P/E powyzej 80. percentyla wlasnej historii.
    Przepuszcza z uwaga: brak danych EPS, brak historii P/E (mniej niz min_months miesiecy).
    """
    if eps_ttm is not None and np.isfinite(eps_ttm) and eps_ttm <= 0:
        return False, "ujemny EPS", np.nan
    if current_pe is None or not np.isfinite(current_pe):
        return True, "brak danych EPS", np.nan
    if current_pe <= 0:
        return False, "ujemny EPS", np.nan
    h = history.dropna()
    h = h[h > 0]
    if len(h) < min_months:
        return True, "brak historii P/E", np.nan
    pct = float((h <= current_pe).mean() * 100)
    if current_pe > np.percentile(h, 80):
        return False, "P/E powyzej p80", pct
    return True, "ok", pct


def eps_fx_ratio(eps_currency: str, price_currency: str, as_of, fx: pd.DataFrame) -> float:
    """Ile jednostek waluty notowania przypada na 1 jednostke waluty EPS (np. USD -> GBX)."""
    from .panel import usd_per_unit
    d = pd.DatetimeIndex([as_of])
    return float(usd_per_unit(eps_currency, d, fx).iloc[0] / usd_per_unit(price_currency, d, fx).iloc[0])


def sector_pe(df: pd.DataFrame) -> pd.DataFrame:
    """P/E sektora = suma kapitalizacji / suma zyskow (kapitalizacja / P/E), tylko spolki z dodatnim P/E."""
    d = df[df["pe"] > 0].copy()
    d["earn"] = d["cap"] / d["pe"]
    g = d.groupby(["sector", "date"])
    return (g["cap"].sum() / g["earn"].sum()).rename("pe").reset_index()
