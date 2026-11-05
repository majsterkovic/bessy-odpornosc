import pandas as pd

START = "2022-01-03"


def cal(n: int) -> pd.DatetimeIndex:
    return pd.bdate_range(START, periods=n)


def panel_from(series: dict, *, delisted=(), currency="USD") -> pd.DataFrame:
    """Dlugi panel z px_usd i volume=1000. None = brak wiersza tego dnia."""
    n = max(len(v) for v in series.values())
    rows = []
    for key, vals in series.items():
        for d, v in zip(cal(n), vals):
            if v is not None:
                rows.append(dict(instrument_id=key, date=d, px_usd=float(v), volume=1000.0, kind="stock",
                                 currency=currency, is_delisted=key in delisted))
    return pd.DataFrame(rows)


EP3 = ["e1", "e2", "e3"]


def metrics_rows(alphas: dict, max_dd: float = -0.1) -> pd.DataFrame:
    """Wiersze wynikow okresowych (valid) dla podanych alf; episode_id = e1, e2, ..."""
    rows = []
    for key, vals in alphas.items():
        for i, a in enumerate(vals, 1):
            rows.append(dict(instrument_id=key, episode_id=f"e{i}", ret=a - 0.2, alpha=a, max_dd=max_dd,
                             valid=True, reason="", stale_share=0.0, ended_early=False))
    return pd.DataFrame(rows)


def make_instr(ids, **over) -> pd.DataFrame:
    n = len(ids)
    d = dict(instrument_id=list(ids), ref_ticker=[f"{i}.US" for i in ids], name=[f"Firma {i}" for i in ids],
             sector=["Technology"] * n, kind=["stock"] * n, isin=[f"ISIN{i}" for i in ids],
             exchange_code=["US"] * n, is_delisted=[False] * n,
             last_date=[pd.Timestamp("2026-10-26")] * n, turnover_usd=[5e6] * n)
    d.update(over)
    return pd.DataFrame(d)


INSTR = make_instr(["A", "B", "MOCNY_TREND", "SLABY_TREND"])
OK_PE = pd.DataFrame({"pe_pass": True, "pe_reason": "ok", "pe": 15.0, "pe_pct": 40.0}, index=INSTR.instrument_id)
