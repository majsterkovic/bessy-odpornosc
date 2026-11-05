"""Panel cen w USD i kontrola jakosci danych (tylko odczyt z bazy)."""
from pathlib import Path

import numpy as np
import pandas as pd

from .db import connect, query_df

CACHE = Path(__file__).resolve().parents[1] / "cache"
PENCE = {"GBp": "GBX", "GBX": "GBX", "ZAc": "ZAc", "ILA": "ILA"}
PENCE_FALLBACK = {"GBX": ("GBP", 0.01), "ZAc": ("ZAR", 0.01), "ILA": ("ILS", 0.01)}


def instruments() -> pd.DataFrame:
    CACHE.mkdir(exist_ok=True)
    f = CACHE / "instrumenty.parquet"
    if f.exists():
        return pd.read_parquet(f)
    df = query_df(
        "select c.instrument_id, c.ref_ticker, c.name, c.kind, c.region, c.currency, c.isin, c.is_delisted, "
        "c.sector, c.industry, c.first_date, c.last_date, l.exchange_code "
        "from v_instruments_canonical c left join listing l on l.instrument_id = c.instrument_id and l.is_primary")
    df["first_date"] = pd.to_datetime(df["first_date"])
    df["last_date"] = pd.to_datetime(df["last_date"])
    df.to_parquet(f)
    return df


def load_window(start, end) -> pd.DataFrame:
    s, e = pd.Timestamp(start).strftime("%Y-%m-%d"), pd.Timestamp(end).strftime("%Y-%m-%d")
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"okno_{s}_{e}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    tmp = CACHE / f"okno_{s}_{e}.csv"
    sql = (f"COPY (select instrument_id, date, adj_close, close, volume from daily_price "
           f"where date between '{s}' and '{e}' and adj_close > 0 and close > 0) TO STDOUT (FORMAT CSV, HEADER)")
    with connect() as c, c.cursor() as cur, open(tmp, "wb") as fh:
        with cur.copy(sql) as cp:
            for chunk in cp:
                fh.write(bytes(chunk))
    d = pd.read_csv(tmp, parse_dates=["date"], dtype={"instrument_id": "int64", "volume": "float64"})
    tmp.unlink()
    d = d.merge(instruments().drop(columns=["first_date", "last_date"]), on="instrument_id", how="inner")
    d.to_parquet(f)
    return d


def fx_table() -> pd.DataFrame:
    df = query_df("select currency, date, eur_rate from fx_rate")
    df["currency"] = df["currency"].str.strip()
    df["date"] = pd.to_datetime(df["date"])
    return df


def _rate(fx: pd.DataFrame, cur: str):
    s = fx.loc[fx["currency"] == cur].set_index("date")["eur_rate"].sort_index()
    return s if len(s) else None


def usd_per_unit(currency: str, dates, fx: pd.DataFrame) -> pd.Series:
    dates = pd.DatetimeIndex(dates)
    if currency == "USD":
        return pd.Series(1.0, index=dates)
    cur = PENCE.get(currency, currency)
    num, mult = _rate(fx, cur), 1.0
    if num is None and cur in PENCE_FALLBACK:
        base, mult = PENCE_FALLBACK[cur]
        num = _rate(fx, base)
    usd = _rate(fx, "USD")
    if num is None or usd is None:
        return pd.Series(np.nan, index=dates)
    return pd.Series(mult * num.asof(dates).to_numpy() / usd.asof(dates).to_numpy(), index=dates)


def to_usd(panel: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    rate = pd.Series(np.nan, index=out.index)
    for cur, idx in out.groupby("currency").groups.items():
        dates = pd.DatetimeIndex(out.loc[idx, "date"].unique())
        m = usd_per_unit(cur, dates, fx)
        rate.loc[idx] = out.loc[idx, "date"].map(m).to_numpy()
    out["px_usd"] = out["adj_close"] * rate
    out["turnover_usd"] = out["close"] * out["volume"] * rate
    return out


def _shift(a: np.ndarray, gid: np.ndarray, k: int) -> np.ndarray:
    """a[i+k] jesli wiersz i+k nalezy do tej samej grupy, inaczej NaN (k>0: przyszlosc, k<0: przeszlosc)."""
    out = np.full(len(a), np.nan)
    if k > 0:
        out[:-k] = a[k:]
        same = np.r_[gid[k:] == gid[:-k], np.zeros(k, bool)]
    else:
        k = -k
        out[k:] = a[:-k]
        same = np.r_[np.zeros(k, bool), gid[k:] == gid[:-k]]
    return np.where(same, out, np.nan)


def _quality_core(px: np.ndarray, vol: np.ndarray | None, gid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Dla wierszy posortowanych po (grupa, data): (dzien_nieruchomy, skok_danych)."""
    prev = _shift(px, gid, -1)
    stale = px == prev
    if vol is not None:
        stale = stale | (vol == 0)  # NaN == 0 -> False (indeksy bez wolumenu)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = px / prev - 1
        lm = np.log(px / prev)
        lp = np.log(px)
        spike = np.zeros(len(px), bool)
        cand = np.abs(r) > 0.5
        if cand.any():
            for k in range(1, 6):
                fwd = _shift(lp, gid, k) - lp
                spike |= cand & (-np.sign(lm) * fwd >= 0.8 * np.abs(lm))
    return stale, spike


def quality(px: pd.Series, volume: pd.Series | None = None) -> tuple[float, bool]:
    p = px.to_numpy(float)
    stale, spike = _quality_core(p, None if volume is None else volume.to_numpy(float), np.zeros(len(p), int))
    return float(stale.mean()), bool(spike.any())


def quality_table(panel: pd.DataFrame, px_col: str = "px_usd") -> pd.DataFrame:
    """Udzial dni nieruchomych i flaga skoku danych dla kazdego instrumentu."""
    p = panel.sort_values(["instrument_id", "date"])
    ids = p["instrument_id"].to_numpy()
    vol = p["volume"].to_numpy(float) if "volume" in p else None
    if vol is not None and "kind" in p:
        vol = np.where(p["kind"].eq("index").to_numpy(), np.nan, vol)  # indeksy nie maja wolumenu
    stale, spike = _quality_core(p[px_col].to_numpy(float), vol, ids)
    g = pd.DataFrame({"instrument_id": ids, "stale": stale, "spike": spike}).groupby("instrument_id")
    return g.agg(stale_share=("stale", "mean"), spike=("spike", "max")).reset_index()


def load_prices(ids, start, end) -> pd.DataFrame:
    """Notowania wybranych instrumentow w oknie (bez pamieci podrecznej), z metadanymi instrumentu."""
    s, e = pd.Timestamp(start).strftime("%Y-%m-%d"), pd.Timestamp(end).strftime("%Y-%m-%d")
    arr = ",".join(str(int(i)) for i in ids)
    sql = (f"COPY (select instrument_id, date, adj_close, close, volume from daily_price "
           f"where instrument_id = any(array[{arr}]::bigint[]) and date between '{s}' and '{e}' "
           f"and adj_close > 0 and close > 0) TO STDOUT (FORMAT CSV, HEADER)")
    CACHE.mkdir(exist_ok=True)
    tmp = CACHE / "_prices.csv"
    with connect() as c, c.cursor() as cur, open(tmp, "wb") as fh:
        with cur.copy(sql) as cp:
            for chunk in cp:
                fh.write(bytes(chunk))
    d = pd.read_csv(tmp, parse_dates=["date"], dtype={"instrument_id": "int64", "volume": "float64"})
    tmp.unlink()
    return d.merge(instruments().drop(columns=["first_date", "last_date"]), on="instrument_id", how="inner")
