import numpy as np
import pandas as pd
import pytest
from conftest import cal, panel_from

from bessy.metrics import bench_return, downside_beta, episode_metrics, weekly_returns


def run(series, bench=-0.20, **kw):
    n = max(len(v) for v in series.values())
    c = cal(n)
    return episode_metrics(panel_from(series, **kw), bench, c[0], c[-1], "t", calendar=c).set_index("instrument_id")


def test_return_alpha_maxdd():
    m = run({"A": [100, 120, 60, 90]}).loc["A"]
    assert m.ret == pytest.approx(-0.10) and m.alpha == pytest.approx(0.10)
    assert m.max_dd == pytest.approx(-0.50) and m.valid and m.reason == ""


def test_late_listing_is_invalid():
    m = run({"A": [None] * 7 + [10, 9], "REF": list(range(100, 109))})
    assert m.loc["A", "reason"] == "brak notowan" and not m.loc["A", "valid"]
    assert m.loc["REF", "valid"]


def test_data_ending_early_invalid_unless_delisted():
    ser = {"A": [100, 90, 80, 50, None, None, None, None, None, None, None, None],
           "REF": list(range(100, 112))}
    assert run(ser).loc["A", "reason"] == "brak notowan"
    m = run(ser, delisted=("A",)).loc["A"]
    assert m.valid and m.ret == pytest.approx(-0.50) and m.ended_early  # zwrot do ostatniego notowania


def test_stale_price_is_invalid():
    m = run({"A": [10.0] * 10 + [10.5], "REF": list(range(100, 111))})
    assert m.loc["A", "reason"] == "nieruchoma cena"


def test_data_spike_is_invalid_but_crash_is_valid():
    m = run({"S": [10, 10.2, 30, 10.5, 10.4, 10.3, 10.2], "C": [10, 5, 2, 1, 0.5, 0.4, 0.3]})
    assert m.loc["S", "reason"] == "skok danych"
    assert m.loc["C", "valid"] and m.loc["C", "ret"] == pytest.approx(-0.97)


def test_missing_usd_rate_marks_pre_1999():
    p = panel_from({"A": [10, 9, 8, 7, 6, 5, 4]}, currency="SEK")
    p.loc[p.index[0], "px_usd"] = np.nan
    c = cal(7)
    m = episode_metrics(p, -0.2, c[0], c[-1], "t", calendar=c).set_index("instrument_id")
    assert m.loc["A", "reason"] == "przed 1999"


def test_pre_1988_dividend_adjustment():
    idx = pd.to_datetime(["1980-01-02", "1981-01-01"])
    flat = pd.Series([100.0, 100.0], index=idx)
    assert bench_return(flat.iloc[:0], flat, idx[0], idx[1]) == pytest.approx(1.04 ** (365 / 365.25) - 1)


def test_bench_return_uses_total_return_after_1988():
    idx = pd.to_datetime(["2000-01-03", "2001-01-03"])
    tr = pd.Series([100.0, 90.0], index=idx)
    gs = pd.Series([100.0, 50.0], index=idx)
    assert bench_return(tr, gs, idx[0], idx[1]) == pytest.approx(-0.10)


def test_downside_beta_uses_only_down_weeks():
    b = pd.Series([-0.02, 0.03, -0.04, 0.01] * 20)
    s = pd.DataFrame({"A": np.where(b < 0, 0.5 * b, 2 * b)})
    assert downside_beta(s, b).loc["A"] == pytest.approx(0.5)


def test_downside_beta_needs_min_weeks():
    b = pd.Series([-0.02, 0.03, -0.04, 0.01] * 10)  # 20 tygodni spadkowych < 26
    s = pd.DataFrame({"A": 0.5 * b})
    assert np.isnan(downside_beta(s, b).loc["A"])


def test_weekly_returns_friday_close():
    p = panel_from({"A": [100, 101, 102, 103, 104, 110, 111, 112, 113, 120]})  # od poniedzialku 2022-01-03
    w = weekly_returns(p)
    assert len(w) == 2 and np.isnan(w["A"].iloc[0])
    assert w["A"].iloc[1] == pytest.approx(120 / 104 - 1)


def test_stale_local_price_is_invalid_even_when_usd_price_moves():
    # kurs walutowy zmienia cene w USD codziennie, ale cena lokalna stoi
    p = panel_from({"A": [10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 11.0],
                    "REF": list(range(100, 111))})
    p["adj_close"] = np.where(p["instrument_id"] == "A", 10.0, p["px_usd"])
    c = cal(11)
    m = episode_metrics(p, -0.2, c[0], c[-1], "t", calendar=c).set_index("instrument_id")
    assert m.loc["A", "reason"] == "nieruchoma cena" and m.loc["REF", "valid"]


def test_spike_on_last_day_of_window_is_caught_with_padding():
    c = cal(16)
    p = panel_from({"S": [100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90 * 5, 90, 89, 88, 87, 86],
                    "REF": list(range(100, 116))})
    # okno konczy sie na indeksie 10 (cena 450 = blad danych), po nim cena wraca do 90
    m = episode_metrics(p, -0.2, c[0], c[10], "t", calendar=c[:11]).set_index("instrument_id")
    assert m.loc["S", "reason"] == "skok danych" and m.loc["REF", "valid"]
    assert m.loc["S", "ret"] == pytest.approx(4.5 - 1)  # zwrot liczony tylko w oknie
