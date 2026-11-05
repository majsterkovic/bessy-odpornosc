"""Rankingi odpornosci: A (kazda bessa) i B (obecny uklad)."""
import numpy as np
import pandas as pd

XTB_EXCHANGES = frozenset("US LSE XETRA PA AS BR MC LS SW ST CO HE OL IR WAR".split())
MIN_WIN_RATE = 0.70
TREND_WEIGHT = 0.25
INFO_COLS = ["ref_ticker", "name", "sector", "exchange_code", "isin"]


def aggregate(metrics: pd.DataFrame, episode_ids: list[str]) -> pd.DataFrame:
    m = metrics[metrics["valid"] & metrics["episode_id"].isin(episode_ids)]
    g = m.groupby("instrument_id")
    return pd.DataFrame({
        "n_valid": g.size(),
        "med_alpha": g["alpha"].median(),
        "med_max_dd": g["max_dd"].median(),
        "win_rate": g["alpha"].apply(lambda s: float((s > 0).mean())),
    }).reset_index()


def composite(agg: pd.DataFrame) -> pd.Series:
    """Srednia percentyli czterech metryk (wagi 0,25). Wymaga kolumny downside_beta."""
    parts = pd.concat([
        agg["med_alpha"].rank(pct=True),
        (-agg["downside_beta"]).rank(pct=True),
        agg["med_max_dd"].rank(pct=True),      # plytszy (mniej ujemny) drawdown = lepiej
        agg["win_rate"].rank(pct=True),
    ], axis=1)
    return parts.mean(axis=1, skipna=False)


def purchasable(instruments: pd.DataFrame, as_of_min: str = "2026-10-20",
                min_turnover_usd: float = 1e6) -> pd.DataFrame:
    d = instruments[
        ~instruments["is_delisted"].astype(bool)
        & (pd.to_datetime(instruments["last_date"]) >= pd.Timestamp(as_of_min))
        & instruments["exchange_code"].isin(XTB_EXCHANGES)
        & (instruments["turnover_usd"] >= min_turnover_usd)
    ].sort_values("turnover_usd", ascending=False)
    has_isin = d["isin"].notna()
    d = pd.concat([d[has_isin].drop_duplicates("isin"), d[~has_isin]])
    return d.sort_index().reset_index(drop=True)


def _prepare(agg, beta, instruments, pe_status, min_valid, apply_purchasable):
    a = agg.copy()
    a["downside_beta"] = a["instrument_id"].map(beta)
    a = a[(a["n_valid"] >= min_valid) & (a["win_rate"] >= MIN_WIN_RATE) & a["downside_beta"].notna()]
    if apply_purchasable:
        a = a[a["instrument_id"].isin(purchasable(instruments)["instrument_id"])]
    a["uwagi"] = ""
    if pe_status is not None:
        pe = pe_status.reindex(a["instrument_id"])
        keep = pe["pe_pass"].fillna(True).to_numpy(bool)
        a = a[keep].copy()
        pe = pe[keep]
        a["pe"], a["pe_pct"] = pe["pe"].to_numpy(), pe["pe_pct"].to_numpy()
        remark = pe["pe_reason"].where(pe["pe_reason"].isin(["brak historii P/E", "brak danych EPS"]), "")
        a["uwagi"] = remark.fillna("").to_numpy()
    return a.reset_index(drop=True)


def _finish(a, instruments, top):
    info = instruments[["instrument_id"] + [c for c in INFO_COLS if c in instruments]].drop_duplicates("instrument_id")
    out = a.merge(info, on="instrument_id", how="left").sort_values("score", ascending=False)
    return out.head(top).reset_index(drop=True)


def rank_a(agg, beta, instruments, pe_status, min_valid: int, top: int = 15,
           apply_purchasable: bool = True) -> pd.DataFrame:
    a = _prepare(agg, beta, instruments, pe_status, min_valid, apply_purchasable)
    a["score"] = composite(a)
    return _finish(a, instruments, top)


def rank_b(agg_twins, beta_twins, trend: pd.DataFrame, instruments, pe_status, min_valid: int,
           top: int = 15, apply_purchasable: bool = True) -> pd.DataFrame:
    a = _prepare(agg_twins, beta_twins, instruments, pe_status, min_valid, apply_purchasable)
    a = a.merge(trend, on="instrument_id", how="left")
    base = composite(a)
    trend_score = pd.concat([a["alpha_od_szczytu_sox"].rank(pct=True), a["alpha_63d"].rank(pct=True)], axis=1).mean(axis=1)
    a["score"] = (1 - TREND_WEIGHT) * base + TREND_WEIGHT * trend_score
    return _finish(a.dropna(subset=["score"]), instruments, top)
