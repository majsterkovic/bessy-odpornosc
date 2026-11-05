"""Metryki zachowania instrumentow w okresie spadkowym."""
import numpy as np
import pandas as pd

from .panel import quality_table

SPXTR_START = pd.Timestamp("1988-02-08")
ASSUMED_DIVIDEND = 0.04
STALE_MAX = 0.20
START_SESSIONS = 5


def bench_return(spxtr: pd.Series, gspc: pd.Series, start, end) -> float:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if len(spxtr) and start >= SPXTR_START:
        return float(spxtr.asof(end) / spxtr.asof(start) - 1)
    r = gspc.asof(end) / gspc.asof(start) - 1
    return float((1 + r) * (1 + ASSUMED_DIVIDEND) ** ((end - start).days / 365.25) - 1)


def episode_metrics(panel: pd.DataFrame, bench_ret: float, peak_date, trough_date, episode_id: str,
                    calendar=None) -> pd.DataFrame:
    """Jeden wiersz na instrument. Panel: okno [szczyt, dolek] (opcjonalnie z zapasem kilku sesji po obu stronach,
    uzywanym tylko do kontroli jakosci) z kolumnami px_usd, volume i opcjonalnie adj_close (cena lokalna)."""
    p = panel.sort_values(["instrument_id", "date"])
    in_window = p["date"].between(pd.Timestamp(peak_date), pd.Timestamp(trough_date))
    cal = np.sort(pd.DatetimeIndex(calendar if calendar is not None else p.loc[in_window, "date"].unique()))
    has_nan = p[in_window].groupby("instrument_id")["px_usd"].apply(lambda s: s.isna().any())
    p = p.dropna(subset=["px_usd"])
    # jakosc danych na cenie lokalnej (kurs walutowy poruszalby cena w USD nawet przy zamrozonym notowaniu)
    # i na oknie rozszerzonym o kilka sesji, by zlapac blad na pierwszym/ostatnim dniu okresu
    q = quality_table(p, "adj_close" if "adj_close" in p else "px_usd").set_index("instrument_id")
    p = p[p["date"].between(pd.Timestamp(peak_date), pd.Timestamp(trough_date))]
    g = p.groupby("instrument_id")
    first_date, last_date = g["date"].first(), g["date"].last()
    first_px, last_px = g["px_usd"].first(), g["px_usd"].last()
    dd = (p["px_usd"] / g["px_usd"].cummax() - 1).groupby(p["instrument_id"]).min()
    delisted = (g["is_delisted"].first() if "is_delisted" in p else pd.Series(False, index=first_px.index)).astype(bool)

    out = pd.DataFrame({"first_date": first_date, "last_date": last_date, "max_dd": dd,
                        "ret": last_px / first_px - 1, "stale_share": q["stale_share"].reindex(first_px.index), "spike": q["spike"].reindex(first_px.index),
                        "is_delisted": delisted})
    out["has_nan"] = has_nan.reindex(out.index).fillna(True).astype(bool)
    start_ok = out["first_date"] <= cal[min(START_SESSIONS, len(cal) - 1)]
    end_reached = out["last_date"] >= cal[max(len(cal) - 1 - START_SESSIONS, 0)]
    out["ended_early"] = ~end_reached
    end_ok = end_reached | out["is_delisted"]
    out["reason"] = np.select(
        [out["has_nan"], ~(start_ok & end_ok), out["stale_share"] > STALE_MAX, out["spike"]],
        ["przed 1999", "brak notowan", "nieruchoma cena", "skok danych"], default="")
    out["valid"] = out["reason"] == ""
    out["alpha"] = out["ret"] - bench_ret
    out["episode_id"] = episode_id
    out = out.reset_index()
    return out[["instrument_id", "episode_id", "ret", "alpha", "max_dd", "valid", "reason", "stale_share",
                "ended_early"]]


def weekly_returns(panel: pd.DataFrame, px_col: str = "px_usd") -> pd.DataFrame:
    """Tygodniowe zwroty (piatek do piatku, ostatnia cena tygodnia). Wiersze: tygodnie, kolumny: instrumenty."""
    wide = panel.pivot(index="date", columns="instrument_id", values=px_col).sort_index()
    return wide.resample("W-FRI").last().pct_change(fill_method=None)


def bench_weekly_returns(spxtr: pd.Series, gspc: pd.Series, start, end) -> pd.Series:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if len(spxtr) and start >= SPXTR_START:
        s = spxtr.loc[start:end].resample("W-FRI").last().pct_change()
    else:
        s = gspc.loc[start:end].resample("W-FRI").last().pct_change() + (1 + ASSUMED_DIVIDEND) ** (7 / 365.25) - 1
    return s


def downside_beta(stock_w: pd.DataFrame, bench_w: pd.Series, min_weeks: int = 26) -> pd.Series:
    """Nachylenie regresji zwrotow instrumentu na zwroty benchmarku w tygodniach spadkowych benchmarku."""
    b = pd.Series(np.asarray(bench_w, float), index=stock_w.index)
    down = (b < 0).to_numpy()
    x = b.to_numpy()[down][:, None]
    y = stock_w.to_numpy(float)[down]
    v = ~np.isnan(y)
    n = v.sum(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        mx = (v * x).sum(0) / n
        y0 = np.where(v, y, 0.0)
        my = y0.sum(0) / n
        cov = (v * (x - mx) * (y0 - my)).sum(0) / n
        var = (v * (x - mx) ** 2).sum(0) / n
        beta = np.where(n >= min_weeks, cov / var, np.nan)
    return pd.Series(beta, index=stock_w.columns)
