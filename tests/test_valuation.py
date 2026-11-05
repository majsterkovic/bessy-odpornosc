import numpy as np
import pandas as pd
import pytest

from bessy.valuation import eps_fx_ratio, pe_filter, pe_monthly, quarterly_eps, sector_pe, split_factor, ttm_eps


def D(*x):
    return pd.to_datetime(list(x))


AAPL = pd.DataFrame({
    "period_type": ["quarterly", "quarterly", "quarterly", "annual", "quarterly", "quarterly", "quarterly"],
    "period_end": D("2024-12-28", "2025-03-29", "2025-06-28", "2025-09-27", "2025-12-27", "2026-03-28", "2026-06-27"),
    "value": [2.40, 1.65, 1.57, 7.46, 2.84, 2.01, 2.02],
    "usable_from": D("2025-01-31", "2025-05-02", "2025-08-01", "2025-10-31", "2026-01-30", "2026-05-01", "2026-07-31")})


def test_q4_is_derived_from_fiscal_year():
    q = quarterly_eps(AAPL).set_index("period_end")
    assert q.loc["2025-09-27", "eps"] == pytest.approx(1.84)


def test_existing_q4_row_is_not_overwritten():
    rows = pd.concat([AAPL, pd.DataFrame({"period_type": ["quarterly"], "period_end": D("2025-09-27"),
                                          "value": [9.99], "usable_from": D("2025-10-31")})])
    assert quarterly_eps(rows).set_index("period_end").loc["2025-09-27", "eps"] == pytest.approx(9.99)


def test_ttm_point_in_time():
    q = quarterly_eps(AAPL)
    assert ttm_eps(q, "2026-08-01") == pytest.approx(8.71)
    assert ttm_eps(q, "2026-07-30") == pytest.approx(1.57 + 1.84 + 2.84 + 2.01)
    assert np.isnan(ttm_eps(q, "2027-06-01"))  # najnowszy kwartal za stary
    assert np.isnan(ttm_eps(q, "2025-02-01"))  # za malo kwartalow


def test_splits_put_eps_on_todays_share_basis():
    # NVDA: split 10:1 2024-06-10; Q1 raportowany przed splitem, Q2-Q3 i rok po splicie
    rows = pd.DataFrame({
        "period_type": ["quarterly", "quarterly", "quarterly", "annual"],
        "period_end": D("2024-04-28", "2024-07-28", "2024-10-27", "2025-01-26"),
        "value": [5.98, 0.67, 0.78, 2.94],
        "usable_from": D("2024-05-29", "2024-08-28", "2024-11-20", "2025-02-26")})
    splits = pd.DataFrame({"ex_date": D("2024-06-10"), "ratio": [10.0]})
    q = quarterly_eps(rows, splits).set_index("period_end")
    assert q.loc["2024-04-28", "eps"] == pytest.approx(0.598)
    assert q.loc["2025-01-26", "eps"] == pytest.approx(2.94 - 0.598 - 0.67 - 0.78)


def test_split_factor():
    s = pd.DataFrame({"ex_date": D("2014-06-09", "2020-08-31"), "ratio": [7.0, 4.0]})
    assert split_factor("2020-08-28", s) == 4.0
    assert split_factor("2014-01-01", s) == 28.0
    assert split_factor("2021-01-01", s) == 1.0
    assert split_factor("2021-01-01", None) == 1.0


def test_pe_monthly_uses_adjusted_price_and_blank_for_loss():
    q = quarterly_eps(AAPL)
    px = pd.Series([87.1], index=D("2026-08-31"))
    assert pe_monthly(px, q).iloc[0] == pytest.approx(10.0)
    loss = q.assign(eps=-1.0)
    assert np.isnan(pe_monthly(px, loss).iloc[0])


def test_pe_filter_reasons():
    h = pd.Series(np.arange(1, 101, dtype=float))
    assert pe_filter(90.0, h)[:2] == (False, "P/E powyzej p80")
    assert pe_filter(50.0, h)[:2] == (True, "ok")
    assert pe_filter(np.nan, h, eps_ttm=-1.0)[:2] == (False, "ujemny EPS")
    assert pe_filter(np.nan, h)[:2] == (True, "brak danych EPS")
    assert pe_filter(20.0, h.iloc[:30])[:2] == (True, "brak historii P/E")
    assert pe_filter(90.0, h)[2] == pytest.approx(90.0)


def test_sector_pe_is_cap_weighted_harmonic():
    df = pd.DataFrame({"sector": ["X", "X", "X"], "date": pd.Timestamp("2026-09-30"),
                       "cap": [100, 100, 50], "pe": [10, 20, -5]})
    assert sector_pe(df).pe.iloc[0] == pytest.approx(200 / 15)


def test_eps_fx_ratio_usd_eps_for_gbx_listing():
    fx = pd.DataFrame({"currency": ["GBX", "USD"], "date": D("2026-10-26", "2026-10-26"), "eur_rate": [0.0115, 0.86]})
    # 1 USD = 0.86/0.0115 pensow
    assert eps_fx_ratio("USD", "GBX", "2026-10-26", fx) == pytest.approx(0.86 / 0.0115)
    assert eps_fx_ratio("USD", "USD", "2026-10-26", fx) == pytest.approx(1.0)
