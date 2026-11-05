import numpy as np
import pandas as pd
import pytest

from bessy.panel import load_window, quality, quality_table, to_usd, usd_per_unit


def fx_frame(rows):
    return pd.DataFrame(rows, columns=["currency", "date", "eur_rate"]).assign(date=lambda d: pd.to_datetime(d.date))


def test_spike_is_flagged_but_bankruptcy_is_not():
    v = pd.Series([1000] * 6)
    assert quality(pd.Series([10, 10.2, 30, 10.5, 10.4, 10.3]), v)[1] is True
    assert quality(pd.Series([10, 5, 2, 1, 0.5, 0.4]), v)[1] is False


def test_stale_share():
    assert quality(pd.Series([10.0] * 10), pd.Series([0] * 10))[0] == pytest.approx(1.0)


def test_index_without_volume_is_not_stale():
    assert quality(pd.Series([10.0, 10.1, 10.2, 10.1]))[0] == pytest.approx(0.0)


def test_pence_and_pre_1999_fallback_from_gbp():
    fx = fx_frame([("GBP", "2020-01-02", 1.18), ("USD", "2020-01-02", 0.89)])
    gbx = usd_per_unit("GBX", pd.to_datetime(["2020-01-03"]), fx)
    assert gbx.iloc[0] == pytest.approx(0.01 * 1.18 / 0.89)
    assert np.isnan(usd_per_unit("GBP", pd.to_datetime(["1998-06-01"]), fx).iloc[0])
    assert usd_per_unit("USD", pd.to_datetime(["1973-01-02"]), fx).iloc[0] == 1.0
    assert np.isnan(usd_per_unit("XXX", pd.to_datetime(["2020-01-03"]), fx).iloc[0])


def test_gbx_row_in_table_is_used_directly():
    fx = fx_frame([("GBX", "2020-01-02", 0.011789), ("USD", "2020-01-02", 0.89342)])
    assert usd_per_unit("GBp", pd.to_datetime(["2020-01-02"]), fx).iloc[0] == pytest.approx(0.011789 / 0.89342)


def test_to_usd_columns():
    fx = fx_frame([("EUR", "2020-01-02", 1.0), ("USD", "2020-01-02", 0.5)])
    p = pd.DataFrame({"instrument_id": [1, 2], "date": pd.to_datetime(["2020-01-03"] * 2),
                      "adj_close": [10.0, 10.0], "close": [10.0, 10.0], "volume": [100, 100],
                      "currency": ["EUR", "USD"]})
    o = to_usd(p, fx).set_index("instrument_id")
    assert o.loc[1, "px_usd"] == pytest.approx(20.0) and o.loc[1, "turnover_usd"] == pytest.approx(2000.0)
    assert o.loc[2, "px_usd"] == pytest.approx(10.0)


def test_quality_table_flags_per_instrument():
    d = pd.bdate_range("2020-01-01", periods=6)
    p = pd.DataFrame({"instrument_id": [1] * 6 + [2] * 6, "date": list(d) * 2,
                      "px_usd": [10, 10.2, 30, 10.5, 10.4, 10.3] + [10, 11, 12, 13, 14, 15],
                      "volume": [1000] * 12})
    q = quality_table(p).set_index("instrument_id")
    assert bool(q.loc[1, "spike"]) and not bool(q.loc[2, "spike"])


@pytest.mark.db
def test_load_window_real_week():
    w = load_window("2022-10-10", "2022-10-14")
    assert {"instrument_id", "date", "adj_close", "close", "volume", "currency", "region", "kind",
            "exchange_code", "ref_ticker", "isin", "is_delisted", "sector"} <= set(w.columns)
    assert w.date.nunique() == 5 and w.instrument_id.nunique() > 10000
    assert (w.adj_close > 0).all()
