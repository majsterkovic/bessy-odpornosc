import pandas as pd

from bessy.pipeline import bear_counts
from tests.conftest import metrics_rows


def test_bear_counts_zlicza_tylko_bessy_z_podanych_okresow():
    m = metrics_rows({"A": [0.1, 0.2, -0.1, 0.3]})   # e1..e4
    ep = pd.DataFrame({"episode_id": ["e1", "e2", "e3", "e4"],
                       "kind": ["bessa", "korekta", "bessa", "bessa"]})
    # ranking B: tylko okresy e1, e2, e3 -> bessy to e1 i e3 (e4 poza zakresem)
    c = bear_counts(m, ep, ["e1", "e2", "e3"]).set_index("instrument_id")
    assert c.loc["A", "n_bessy"] == 2
    assert c.loc["A", "win_bessy"] == 0.5


def test_mask_invalid_weeks_blanks_columns_of_invalid_periods():
    from bessy.pipeline import mask_invalid_weeks
    wk = pd.DataFrame({"1": [0.1, -0.1], "2": [0.2, -0.2]}, index=pd.date_range("2022-01-07", periods=2, freq="W-FRI"))
    m = pd.DataFrame({"instrument_id": [1, 2], "episode_id": ["e", "e"], "valid": [True, False]})
    out = mask_invalid_weeks(wk, m, "e")
    assert out["1"].notna().all() and out["2"].isna().all()


def test_sens_summary_counts_overlap_and_lists_difference():
    from bessy.pipeline import sens_summary
    s = sens_summary(["a", "b", "c", "d"], ["b", "c", "x", "y"], n=3)
    assert s["overlap"] == 2 and s["both"] == ["b", "c"] and s["only_b"] == ["x"]


def test_drop_equivalent_duplicates_keeps_one_slot_per_fund():
    from bessy.pipeline import drop_equivalent_duplicates
    rows = [("CMDY", "us", ["CMOD"]), ("CMOD", "eu", []), ("SGLD", "eu", []), ("IAU", "us", ["SGLD", "X"]), ("BCD", "us", ["BCFU"])]
    assert drop_equivalent_duplicates(rows) == ["CMDY", "SGLD", "BCD"]


def test_episode_metrics_has_no_rows_for_instruments_only_in_padding():
    import numpy as np
    from conftest import cal, panel_from
    from bessy.metrics import episode_metrics
    c = cal(16)
    p = panel_from({"A": list(range(100, 116)), "PAD": [None] * 12 + [5, 6, 7, 8]})
    m = episode_metrics(p, -0.1, c[2], c[10], "t", calendar=c[2:11])
    assert list(m["instrument_id"]) == ["A"] and not np.isnan(m["ret"]).any()


def test_funnel_steps_counts_each_stage_in_order():
    from bessy.pipeline import funnel_steps
    ins = pd.DataFrame({"instrument_id": [1, 2, 3, 4, 5, 6], "kind": ["stock"] * 5 + ["etf"]})
    cand = pd.DataFrame({"instrument_id": [1, 2, 3, 4], "kind": ["stock"] * 4})
    aa = pd.DataFrame({"instrument_id": [1, 2, 3], "n_valid": [5, 4, 3], "win_rate": [0.9, 0.5, 1.0]})
    pe = pd.DataFrame({"pe_pass": [True, False]}, index=pd.Index([1, 2], name="instrument_id"))
    steps = funnel_steps(ins, cand, aa, pe, top=1)
    assert [s["key"] for s in steps] == ["akcje_w_bazie", "kandydaci", "min4", "win70", "pe_ok", "top"]
    assert [s["n"] for s in steps] == [5, 4, 2, 1, 1, 1]


def test_drop_cap_outliers_removes_absurd_and_spiking_caps():
    from bessy.pipeline import drop_cap_outliers
    dates = pd.date_range("2020-01-31", periods=24, freq="ME")
    a = pd.DataFrame({"instrument_id": 1, "date": dates, "cap_eur": [1e9] * 24})
    a.loc[10, "cap_eur"] = 5e11                       # skok x500 wzgledem mediany instrumentu
    b = pd.DataFrame({"instrument_id": 2, "date": dates, "cap_eur": [9.7e12] * 24})   # kap. w walucie lokalnej (np. TWD)
    c = pd.DataFrame({"instrument_id": 3, "date": dates, "cap_eur": [3e9 * (1 + 0.05 * i) for i in range(24)]})  # zwykly wzrost
    out = drop_cap_outliers(pd.concat([a, b, c], ignore_index=True))
    assert set(out["instrument_id"]) == {1, 3}
    assert len(out[out.instrument_id == 1]) == 23 and len(out[out.instrument_id == 3]) == 24


def test_pe_reason_tables_split_rejected_from_passed_and_reconcile_with_funnel():
    from bessy.pipeline import funnel_steps, pe_reason_tables
    ins = pd.DataFrame({"instrument_id": range(1, 8), "kind": ["stock"] * 7})
    cand = ins.copy()
    aa = pd.DataFrame({"instrument_id": range(1, 8), "n_valid": [5] * 7, "win_rate": [1.0] * 6 + [0.2]})
    pe = pd.DataFrame({"pe_pass": [True, True, True, False, False, True], "pe_reason": ["ok", "brak danych EPS", "brak historii P/E", "ujemny EPS", "P/E powyzej p80", "ok"]},
                      index=pd.Index([1, 2, 3, 4, 5, 6], name="instrument_id"))
    t = pe_reason_tables(aa, pe)
    assert sum(r["n"] for r in t["rejected"]) == 2 and {r["reason"] for r in t["rejected"]} == {"ujemny zysk (EPS)", "P/E powyżej własnego 80. percentyla"}
    assert sum(r["n"] for r in t["passed"]) == 4
    steps = funnel_steps(ins, cand, aa, pe, top=1)
    win, pe_ok = [s["n"] for s in steps if s["key"] in ("win70", "pe_ok")]
    assert win - pe_ok == sum(r["n"] for r in t["rejected"])
