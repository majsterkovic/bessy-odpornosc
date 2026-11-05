import numpy as np
import pandas as pd
import pytest
from conftest import EP3, INSTR, OK_PE, make_instr, metrics_rows

from bessy.scoring import aggregate, composite, purchasable, rank_a, rank_b


def test_aggregate_uses_only_valid_rows_of_given_episodes():
    m = metrics_rows({"A": [0.1, -0.2, 0.3]})
    m.loc[m.episode_id == "e2", "valid"] = False
    a = aggregate(m, EP3).set_index("instrument_id").loc["A"]
    assert a.n_valid == 2 and a.win_rate == 1.0 and a.med_alpha == pytest.approx(0.2)
    assert aggregate(m, ["e1"]).set_index("instrument_id").loc["A", "n_valid"] == 1


def test_win_rate_below_70pct_is_rejected():
    m = metrics_rows({"A": [0.1, 0.2, -0.1], "B": [0.1, 0.1, 0.1]})
    r = rank_a(aggregate(m, EP3), beta=pd.Series({"A": 0.3, "B": 0.5}), instruments=INSTR,
               pe_status=OK_PE, min_valid=3)
    assert list(r.instrument_id) == ["B"]


def test_min_valid_periods_is_enforced():
    m = metrics_rows({"A": [0.1, 0.2], "B": [0.1, 0.1, 0.1]})
    r = rank_a(aggregate(m, EP3), pd.Series({"A": 0.3, "B": 0.5}), INSTR, OK_PE, min_valid=3)
    assert list(r.instrument_id) == ["B"]


def test_composite_prefers_dominant():
    agg = pd.DataFrame({"med_alpha": [0.2, 0.1, 0.0], "downside_beta": [0.2, 0.5, 0.9],
                        "med_max_dd": [-0.1, -0.2, -0.3], "win_rate": [1.0, 0.8, 0.7]}, index=list("XYZ"))
    c = composite(agg)
    assert c.idxmax() == "X" and c.idxmin() == "Z"


def test_pe_filter_rejects_expensive_and_keeps_remark():
    m = metrics_rows({"A": [0.1] * 3, "B": [0.2] * 3})
    pe = OK_PE.copy()
    pe.loc["A", ["pe_pass", "pe_reason"]] = [False, "P/E powyzej p80"]
    pe.loc["B", "pe_reason"] = "brak historii P/E"
    r = rank_a(aggregate(m, EP3), pd.Series({"A": 0.3, "B": 0.5}), INSTR, pe, min_valid=3)
    assert list(r.instrument_id) == ["B"] and "brak historii P/E" in r.iloc[0].uwagi


def test_etf_ranking_without_pe_and_purchase_filters():
    m = metrics_rows({"A": [0.1] * 3})
    r = rank_a(aggregate(m, EP3), pd.Series({"A": 0.3}), instruments=INSTR.assign(exchange_code="F"),
               pe_status=None, min_valid=3, apply_purchasable=False)
    assert list(r.instrument_id) == ["A"]


def test_rank_b_weights_trend_25pct():
    m = metrics_rows({"MOCNY_TREND": [0.1, 0.1], "SLABY_TREND": [0.1, 0.1]})
    trend = pd.DataFrame({"instrument_id": ["MOCNY_TREND", "SLABY_TREND"],
                          "alpha_od_szczytu_sox": [0.10, -0.10], "alpha_63d": [0.05, -0.05]})
    r = rank_b(aggregate(m, ["e1", "e2"]), pd.Series({"MOCNY_TREND": 0.4, "SLABY_TREND": 0.4}),
               trend, INSTR, OK_PE, min_valid=2)
    assert list(r.instrument_id) == ["MOCNY_TREND", "SLABY_TREND"]
    assert r.score.iloc[0] - r.score.iloc[1] == pytest.approx(0.25 * 0.5)


def test_duplicate_isin_keeps_higher_turnover():
    inst = make_instr([1, 2], isin=["US0378331005"] * 2, exchange_code=["US", "XETRA"], turnover_usd=[5e9, 2e6])
    assert list(purchasable(inst).instrument_id) == [1]


def test_exchange_outside_xtb_list_is_dropped():
    assert purchasable(INSTR.assign(exchange_code="F")).empty


def test_delisted_stale_and_illiquid_are_dropped():
    inst = make_instr([1, 2, 3, 4], is_delisted=[True, False, False, False],
                      last_date=[pd.Timestamp("2026-10-26")] * 2 + [pd.Timestamp("2026-10-01")] + [pd.Timestamp("2026-10-26")],
                      turnover_usd=[5e6, 5e6, 5e6, 1e5])
    assert list(purchasable(inst).instrument_id) == [2]
