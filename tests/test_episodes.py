import pandas as pd
import pytest

from bessy.db import index_series
from bessy.episodes import find_episodes


def s(vals):
    return pd.Series(vals, index=pd.bdate_range("2000-01-03", periods=len(vals)), dtype=float)


def test_bear_confirmed_by_new_peak_and_recovery_date():
    x = s([100, 90, 80, 95, 104, 99, 100, 105])
    e = find_episodes(x)
    assert len(e) == 1
    r = e.iloc[0]
    assert (r.peak, r.trough, r.kind, r.confirmed) == (100, 80, "bessa", True)
    assert r.depth == pytest.approx(-0.20)
    assert r.recovery_date == x.index[4]  # pierwszy close >= 100 po dolku
    assert r.days_to_recovery == (x.index[4] - x.index[2]).days


def test_correction_ends_on_new_peak_without_30pct():
    e = find_episodes(s([100, 84, 101]))
    assert e.iloc[0].kind == "korekta" and e.iloc[0].confirmed


def test_no_episode_below_15pct():
    assert find_episodes(s([100, 86, 110])).empty


def test_open_episode_at_end():
    r = find_episodes(s([100, 70, 75])).iloc[0]
    assert not r.confirmed and pd.isna(r.recovery_date)


def test_mid_bear_rally_below_30pct_does_not_split():
    e = find_episodes(s([100, 60, 75, 50, 60, 101]))
    assert len(e) == 1 and e.iloc[0].trough == 50


def test_rebound_30pct_closes_episode_before_recovery():
    e = find_episodes(s([100, 50, 66, 70, 110]))
    r = e.iloc[0]
    assert r.confirmed and r.trough == 50 and r.recovery_date == s([0] * 5).index[4]


@pytest.mark.db
@pytest.mark.parametrize("peak,trough,depth", [
    ("2000-03-24", "2002-10-09", -0.491), ("2007-10-09", "2009-03-09", -0.568),
    ("2020-02-19", "2020-03-23", -0.339), ("2022-01-03", "2022-10-12", -0.254)])
def test_known_sp500_bears(peak, trough, depth):
    e = find_episodes(index_series("GSPC.INDX")).set_index("episode_id")
    assert str(e.loc[peak].trough_date.date()) == trough
    assert e.loc[peak].depth == pytest.approx(depth, abs=0.005)
