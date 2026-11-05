import numpy as np
import pandas as pd
import pytest
from conftest import EP3, metrics_rows

from bessy.db import query_df
from bessy.etf import SECTOR_INDEX, etf_universe, is_excluded, sector_table, ucits_matches


@pytest.mark.parametrize("name,excluded", [
    ("ProShares UltraShort S&P500", True), ("Direxion Daily Semiconductor Bear 3X", True),
    ("CBOE Volatility Index", True), ("CBOE 13 Week Treasury Bill Yield Index", True),
    ("iShares MSCI USA Min Vol Factor ETF", False), ("Utilities Select Sector SPDR® Fund", False), ("Lyxor Ibex 35 Doble Inverso Diario UCITS ETF", True),
    ("Amundi ETF Leveraged MSCI USA Daily Levier 2", True),
    ("iShares Short Treasury Bond ETF", False),
    ("Vanguard FTSE All-World High Dividend Yield UCITS ETF", False),
    ("US Dollar Currency Index", True), ("Invesco S&P 500® Low Volatility ETF", False),
    ("iShares MSCI World Minimum Volatility UCITS ETF", False), ("VelocityShares Daily Inverse VIX ETN", True),
    ("ProShares VIX Short-Term Futures ETF", True), ("Beta ETF WIG20Short PCIF", True),
    ("Nasdaq 100 Daily Covered Call UCITS ETF USD Dis", False), ("AXS 1.25X NVDA Bear Daily ETF", True),
    ("Daily NVDA Bull 2X ETF", True), ("Gold Bullion Securities EUR", False),
    ("Franklin Euro Short Maturity UCITS ETF", False), ("Leverage Shares -3x Short Semiconductors ETC", True),
    ("Lyxor Daily ShortDAX x2 UCITS ETF", True), ("Xtrackers ShortDAX Daily Swap UCITS ETF 1C", True),
    ("Lyxor UCITS Daily Leverage CAC 40", True), ("Amundi Shortterm Bond UCITS ETF", False)])
def test_exclusions(name, excluded):
    assert is_excluded(name, "") is excluded


def test_etf_universe_keeps_etf_and_index_only_and_drops_excluded():
    inst = pd.DataFrame({"instrument_id": [1, 2, 3, 4], "kind": ["etf", "index", "stock", "etf"],
                         "name": ["Utilities Select Sector SPDR", "S&P 500 Utilities", "Firma", "ProShares UltraShort QQQ"],
                         "ref_ticker": ["XLU.US", "SPLRCU.INDX", "F.US", "QID.US"]})
    assert list(etf_universe(inst).instrument_id) == [1, 2]


def test_ucits_match_threshold_and_order():
    rng = np.random.default_rng(0)
    us = pd.Series(rng.normal(0, 0.02, 156))
    eu = pd.DataFrame({"good": us + rng.normal(0, 0.002, 156), "bad": rng.normal(0, 0.02, 156),
                       "short": us.iloc[:50]})
    m = ucits_matches(us, eu)
    assert list(m.instrument_id) == ["good"] and m["corr"].iloc[0] > 0.95 and m.n_weeks.iloc[0] == 156


def test_sector_table_median_alpha_and_win_rate():
    m = metrics_rows({"T": [0.1, -0.1, 0.2], "E": [0.3, 0.4, 0.5]})
    inst = pd.DataFrame({"instrument_id": ["T", "E"], "ref_ticker": [SECTOR_INDEX["Technology"], SECTOR_INDEX["Energy"]]})
    t = sector_table(m, inst, EP3).set_index("sector")
    assert t.loc["Energy", "win_rate"] == 1.0 and t.loc["Energy", "med_alpha"] == pytest.approx(0.4)
    assert t.loc["Technology", "win_rate"] == pytest.approx(2 / 3)


@pytest.mark.db
def test_sector_index_tickers_exist_in_db():
    found = set(query_df("select ref_ticker from instrument where ref_ticker = any(%(t)s)",
                         {"t": list(SECTOR_INDEX.values())}).ref_ticker)
    assert found == set(SECTOR_INDEX.values())


@pytest.mark.parametrize("name,industry,ticker,flag", [
    ("BH Macro Limited", None, "BHMG.LSE", True), ("Nuveen Select Tax-Free Income Portfolio", "Asset Management", "NXP.US", True),
    ("Ruffer Investment Company Limited", "Asset Management", "RICA.LSE", True), ("Capital Gearing Trust", None, "CGT.LSE", True),
    ("Acme Acquisition Corp", "Shell Companies", "ACQ.US", True), ("Coca-Cola Co.", None, "0QZK.LSE", True),
    ("Northern Trust Corporation", "Asset Management", "NTRS.US", False), ("Consolidated Edison Inc", "Utilities - Regulated Electric", "ED.US", False),
    ("Ares Capital Corporation", "Asset Management", "ARCC.US", False), ("Berkshire Hathaway Inc", "Insurance - Diversified", "BRK-B.US", False),
    ("Pershing Square Holdings Ltd", None, "PSH.LSE", False)])
def test_fund_like_and_foreign_lines(name, industry, ticker, flag):
    from bessy.etf import is_fund_like
    assert is_fund_like(name, industry, ticker) is flag


@pytest.mark.parametrize("name,cls", [
    ("SPDR® Bloomberg 1-3 Month T-Bill ETF", "obligacje i inne"), ("iShares $ Treasury Bond 7-10yr UCITS ETF USD (Dist)", "obligacje i inne"),
    ("Xtrackers II USD Overnight Rate Swap UCITS ETF 1C", "obligacje i inne"), ("iShares Floating Rate Bond ETF", "obligacje i inne"),
    ("SPDR Gold Shares", "surowce i waluty"), ("Invesco CurrencyShares® Japanese Yen Trust", "surowce i waluty"),
    ("Invesco CurrencyShares Euro Trust", "surowce i waluty"), ("Teucrium Soybean", "surowce i waluty"),
    ("AGFiQ U.S. Market Neutral Anti-Beta Fund", "alternatywy"), ("Cambria Tail Risk ETF", "alternatywy"),
    ("Utilities Select Sector SPDR® Fund", "akcje"), ("Invesco S&P 500® Low Volatility ETF", "akcje"),
    ("iShares MSCI World Quality Dividend UCITS ETF", "akcje"), ("VanEck Gold Miners ETF", "surowce i waluty")])
def test_etf_class(name, cls):
    from bessy.etf import etf_class
    assert etf_class(name) == cls


def test_etf_class_uses_correlation_when_known():
    from bessy.etf import etf_class
    assert etf_class("iShares MBS ETF", 0.2) == "obligacje i inne"
    assert etf_class("iShares Core Dividend Income ETF", 0.8) == "akcje"
    assert etf_class("Teucrium Sugar", 0.1) == "obligacje i inne" or etf_class("Teucrium Sugar", 0.1) == "surowce i waluty"
    assert etf_class("SPDR Gold Shares", 0.9) == "surowce i waluty"
    assert etf_class("Invesco Senior Loan ETF", 0.62) == "obligacje i inne"
    assert etf_class("iShares 0-5 Year High Yield Corporate Bond ETF", 0.72) == "obligacje i inne"
    assert etf_class("Innovator S&P 500 Power Buffer ETF - July", 0.95) == "alternatywy"
    assert etf_class("iShares Core Conservative Allocation ETF", 0.75) == "alternatywy"
    assert etf_class("Invesco S&P 500 Low Volatility ETF", 0.78) == "akcje"


def test_dedupe_by_correlation_keeps_best_ranked():
    from bessy.etf import dedupe_by_correlation
    rng = np.random.default_rng(1)
    a = pd.Series(rng.normal(0, 0.02, 120))
    w = pd.DataFrame({"x1": a, "x2": a + rng.normal(0, 0.001, 120), "y": rng.normal(0, 0.02, 120)})
    assert dedupe_by_correlation(["x1", "x2", "y"], w, 0.97) == ["x1", "y"]
    assert dedupe_by_correlation(["y", "x2", "x1"], w, 0.97) == ["y", "x2"]


@pytest.mark.parametrize("name", ["WisdomTree Bloomberg U.S. Dollar Bullish Fund", "Cambria Tail Risk ETF",
                                  "Some Bearish Equity Fund"])
def test_bullish_bearish_and_tail_risk_funds_are_excluded(name):
    assert is_excluded(name, "")


def test_fund_behaving_inversely_to_market_gets_its_own_class():
    from bessy.etf import etf_class
    assert etf_class("Neutral Name Fund", -0.7) == "odwrotny"
    assert etf_class("Neutral Name Fund", 0.3) == "obligacje i inne"


@pytest.mark.parametrize("isin,ticker,ok", [
    ("IE00B4L5Y983", "IWDA.LSE", True), ("LU0274208692", "XDWD.XETRA", True), ("DE000A0S9GB0", "4GLD.XETRA", True),
    ("US78462F1030", "0KZC.LSE", False), (None, "XYZ.PA", False), ("IE00B4L5Y983", "0LO6.LSE", False),
    ("US9229083632", "VOO.US", False)])
def test_ucits_candidate_requires_eu_isin_and_real_listing(isin, ticker, ok):
    from bessy.etf import is_eu_domiciled
    assert is_eu_domiciled(isin, ticker) is ok


def test_ucits_match_uses_multi_week_returns_to_absorb_close_time_mismatch():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2023-01-06", periods=156, freq="W-FRI")
    us = pd.Series(rng.normal(0, 0.02, 156), index=idx)
    eu = pd.DataFrame({"E": 0.7 * us + 0.3 * us.shift(1).fillna(0)})   # inny moment wyceny
    assert len(ucits_matches(us, eu, min_corr=0.95)) == 0               # tygodniowo za malo
    assert len(ucits_matches(us, eu, min_corr=0.95, horizon=4)) == 1    # 4-tygodniowo wystarcza


def test_ucits_match_rejects_fund_with_very_different_volatility():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2023-01-06", periods=156, freq="W-FRI")
    us = pd.Series(rng.normal(0, 0.02, 156), index=idx)
    eu = pd.DataFrame({"BUFOR": 0.4 * us})   # korelacja 1, zmiennosc 40%
    assert len(ucits_matches(us, eu, min_corr=0.90)) == 0


@pytest.mark.parametrize("name,corr,cls", [
    ("iShares $ Treasury Bond 1-3yr UCITS ETF CHF Hedged (Acc)", 0.01, "obligacje i inne"),
    ("WisdomTree Agriculture EUR", 0.18, "surowce i waluty"),
    ("Lyxor Euro Cash UCITS ETF", 0.14, "obligacje i inne"),
    ("iShares Euro Stoxx 50 UCITS ETF", 0.85, "akcje"),
    ("AGFiQ Global Hedge Fund Replication", 0.6, "alternatywy")])
def test_etf_class_regressions(name, corr, cls):
    from bessy.etf import etf_class
    assert etf_class(name, corr) == cls


def test_eu_domicile_without_isin_needs_ucits_in_name():
    from bessy.etf import is_eu_domiciled
    assert is_eu_domiciled(None, "VWRA.SW", "Vanguard FTSE All-World UCITS ETF") is True
    assert is_eu_domiciled(None, "0KZC.LSE", "SPDR UCITS") is False
    assert is_eu_domiciled(None, "XYZ.PA", "Some ETF") is False
