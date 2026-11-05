from datetime import date

import numpy as np
import pandas as pd
import pytest

from bessy.db import index_series
from bessy.episodes import find_episodes
from bessy.macro import (current_state, election_day, macro_flags, max_12m_change, midterm_seasonality,
                         oil_proxy, overlaps_midterm, pick_twins, rel_change)


def test_election_days():
    assert election_day(2026) == date(2026, 11, 3)
    assert election_day(2022) == date(2022, 11, 8)
    assert election_day(2018) == date(2018, 11, 6)


def test_midterm_overlap():
    assert overlaps_midterm(pd.Timestamp("2000-03-24"), pd.Timestamp("2002-10-09"))
    assert not overlaps_midterm(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-03-23"))
    assert not overlaps_midterm(pd.Timestamp("2007-10-09"), pd.Timestamp("2009-03-09"))


def test_max_12m_change_and_missing_history():
    idx = pd.date_range("2000-01-01", "2002-12-31")
    s = pd.Series(np.where(idx < "2001-06-01", 50.0, 100.0), index=idx)
    assert max_12m_change(s, "2001-07-01", "2001-08-01") == pytest.approx(1.0)
    assert np.isnan(max_12m_change(s, "2000-06-01", "2000-07-01"))


def test_oil_proxy_is_continuous():
    g = pd.Series([10.0, 20, 40], index=pd.to_datetime(["1990-12-28", "1990-12-31", "1991-01-02"]))
    b = pd.Series([100.0, 200], index=pd.to_datetime(["1990-12-31", "1991-01-02"]))
    p = oil_proxy(b, g)
    assert p.loc["1990-12-28"] == pytest.approx(50.0) and p.loc["1991-01-02"] == 200


def test_rel_change_uses_ratio_and_tolerates_short_start():
    idx = pd.date_range("2000-01-03", "2003-01-03", freq="D")
    num = pd.Series(np.where(idx < "2001-06-01", 100.0, 150.0), index=idx)
    den = pd.Series(100.0, index=idx)
    assert rel_change(num, den, "2002-06-01") == pytest.approx(0.5)
    # koniec 23 miesiace po starcie serii: tolerancja 62 dni, uzywa pierwszego dnia serii
    assert rel_change(num, den, "2001-12-03") == pytest.approx(0.5)
    assert np.isnan(rel_change(num, den, "2000-06-01"))


def test_pick_twins_needs_two_factors_and_sorts_by_distance():
    f = pd.DataFrame({"episode_id": ["1990-07-16", "2020-02-19", "2022-01-03"],
                      "peak_date": pd.to_datetime(["1990-07-16", "2020-02-19", "2022-01-03"]),
                      "oil_12m_max": [1.2, -0.3, 1.1], "tech_rs_24m": [0.0, 0.2, 0.18],
                      "midterm": [True, False, True], "n_factors": [2, 1, 3]})
    t = pick_twins(f, {"oil_12m": 1.2, "tech_rs_24m": 0.2, "midterm": True})
    assert list(t.episode_id) == ["2022-01-03", "1990-07-16"]


def test_pick_twins_drops_nan_factor_and_old_peaks():
    f = pd.DataFrame({"episode_id": ["a", "b"], "peak_date": pd.to_datetime(["1965-01-01", "1990-01-01"]),
                      "oil_12m_max": [1.0, np.nan], "tech_rs_24m": [0.1, 0.1],
                      "midterm": [True, True], "n_factors": [2, 2]})
    assert pick_twins(f, {"oil_12m": 1.0, "tech_rs_24m": 0.1, "midterm": True}).empty


def test_seasonality_shapes():
    idx = pd.bdate_range("1950-01-02", "2026-10-26")
    s = pd.Series(100 * 1.0004 ** np.arange(len(idx)), index=idx)
    m, post = midterm_seasonality(s)
    assert len(m) == 12 and {"mean_wybory", "median_wybory", "mean_inne", "median_inne"} <= set(m.columns)
    r = post.set_index("year")
    assert r.loc[2022, "r3m"] < r.loc[2022, "r6m"] < r.loc[2022, "r12m"]
    assert np.isnan(r.loc[2026, "r3m"])


@pytest.mark.db
def test_2022_is_a_twin_on_real_data():
    gspc, ixic = index_series("GSPC.INDX"), index_series("IXIC.INDX")
    oil = oil_proxy(index_series("BCOMCO.INDX"), index_series("SPGSCI.INDX"))
    flags = macro_flags(find_episodes(gspc), oil, ixic, gspc)
    twins = pick_twins(flags, current_state(oil, ixic, gspc, "2026-10-26"))
    print(flags[["episode_id", "oil_12m_max", "tech_rs_24m", "midterm", "n_factors", "brief_match"]]
          .round(3).to_string())
    print(twins[["episode_id", "n_factors", "distance"]].to_string())
    assert "2022-01-03" in set(twins.episode_id)
