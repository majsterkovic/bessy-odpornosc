import json
import os

import numpy as np
import pandas as pd
import pytest

from bessy.export_web import build_payloads, series_payload

EP = pd.DataFrame({
    "episode_id": ["1929-09-16", "1973-01-11", "2022-01-03", "2018-09-20"],
    "peak_date": ["1929-09-16", "1973-01-11", "2022-01-03", "2018-09-20"],
    "trough_date": ["1929-11-13", "1974-10-03", "2022-10-12", "2018-12-24"],
    "depth": [-0.45, -0.48, -0.25, -0.19], "days_to_trough": [58, 630, 282, 95], "days_to_recovery": [9079, 2114, np.nan, 100],
    "kind": ["bessa", "bessa", "bessa", "korekta"], "n_factors": [0, 2, 2, 2],
    "oil_shock": [False, True, True, True], "tech_hot": [False, False, True, False], "midterm": [False, True, True, True],
})


def _row(i, **kw):
    r = dict(instrument_id=i, n_valid=4, med_alpha=0.2, med_max_dd=-0.1, win_rate=1.0, downside_beta=0.3, uwagi="",
             pe=np.nan, pe_pct=np.nan, ref_ticker=f"T{i}.US", name=f"Firma {i}", sector=None, exchange_code="US",
             waluta="USD", n_bessy=2)
    r.update(kw)
    return r


@pytest.fixture
def wyniki(tmp_path):
    ctx = dict(as_of="2026-10-26", podsumowanie="Tekst", stan=pd.DataFrame({"indeks": ["S&P 500"], "ticker": ["GSPC.INDX"], "data": ["2026-10-26"],
               "poziom": [7676.0], "ath": [7818.0], "data_ath": ["2026-10-06"], "od_ath": [-0.018], "r_3m": [0.03], "r_12m": [0.13]}),
               stan_tekst="x", czynniki_teraz=pd.DataFrame({"okres": ["dziś"], "ropa": [1.2], "tech": [0.07], "wybory": ["tak"],
               "czynniki": [2], "odleglosc": [np.nan]}), sezonowosc_mies=pd.DataFrame({"miesiac": ["sty"], "mean_wybory": [0.01]}),
               po_wyborach=pd.DataFrame({"year": [2022], "r3m": [0.1]}), po_wyborach_tekst="p", blizniaki_tekst="b", brief_tekst="br",
               sektory_a=pd.DataFrame({"sector": ["Utilities"], "med_alpha": [0.1]}), sektory_b=pd.DataFrame({"sector": ["Utilities"], "med_alpha": [0.2]}),
               sektory_pe=pd.DataFrame({"sector": ["Utilities"], "pe_teraz": [19.0], "pokrycie": [0.5]}), sektory_pe_tekst="pe",
               top_a_spolki=pd.DataFrame([_row(1), _row(2, pe=15.0, uwagi="brak danych EPS")]),
               top_b_spolki=pd.DataFrame([_row(1, alpha_od_szczytu_sox=0.1, alpha_63d=0.02)]),
               top_a_etf=pd.DataFrame([_row(3, classe="akcje", corr_spx=0.7, odpowiedniki_ucits="XYZ.LSE (0.97)", currency="USD")]),
               top_b_etf=pd.DataFrame([_row(3, classe="akcje", corr_spx=0.7, odpowiedniki_ucits=None, currency="USD")]),
               walidacja="w", zalozenia=["z1", "z2"])
    k = dict(ctx=ctx, oos=dict(n=5, spearman=0.4, kwintyle=[]), sens=dict(overlap15=8, both=["A"]),
             kolejnosc_a=["1973-01-11", "2022-01-03", "2018-09-20"], kolejnosc_b=["1973-01-11", "2022-01-03"],
             lejek=[dict(key="kandydaci", label="K", n=10, note="")],
             pe_tabele=dict(rejected=[dict(reason="ujemny zysk (EPS)", n=2)], passed=[dict(reason="przeszło bez uwag", n=5)]))
    from bessy.serialize import to_jsonable
    (tmp_path / "kontekst.json").write_text(json.dumps(to_jsonable(k), allow_nan=False), encoding="utf-8")
    EP.to_csv(tmp_path / "epizody.csv", index=False)
    pd.DataFrame({"instrument_id": [1, 2, 3], "pe_reason": ["ujemny EPS", "P/E powyzej p80", "ujemny EPS"]}).to_csv(tmp_path / "pe_status.csv", index=False)
    m = pd.DataFrame([dict(instrument_id=1, episode_id=e, alpha=a, valid=v) for e, a, v in
                      [("1973-01-11", 0.3, True), ("2022-01-03", 0.1, True), ("2018-09-20", 0.2, True), ("1980-11-28", 0.9, True), ("2000-03-24", 0.5, False)]])
    m.to_csv(tmp_path / "metryki.csv", index=False)
    return tmp_path


def test_payload_keys_and_meta(wyniki):
    p = build_payloads(wyniki, wyniki / "metryki.csv")
    assert set(p) == {"meta", "market", "episodes", "twins", "sectors", "funnel", "validation", "lists"}
    assert p["meta"]["as_of"] == "2026-10-26" and p["meta"]["version"] == 1 and p["meta"]["notes"] == ["z1", "z2"]
    assert p["market"]["indices"][0]["ticker"] == "GSPC.INDX"


def test_episodes_flag_ranking_a_and_twins(wyniki):
    rows = {r["episode_id"]: r for r in build_payloads(wyniki, wyniki / "metryki.csv")["episodes"]["rows"]}
    assert len(rows) == 4 and rows["1929-09-16"]["in_ranking_a"] is False
    assert rows["2018-09-20"]["in_ranking_a"] is True and rows["2018-09-20"]["twin"] is False
    assert rows["1973-01-11"]["twin"] is True


def test_lists_row_has_per_episode_alpha_only_for_ranking_periods(wyniki):
    lists = build_payloads(wyniki, wyniki / "metryki.csv")["lists"]
    a = {e["episode_id"] for e in lists["stocks_a"][0]["per_episode"]}
    b = {e["episode_id"] for e in lists["stocks_b"][0]["per_episode"]}
    assert a == {"1973-01-11", "2022-01-03", "2018-09-20"} and b == {"1973-01-11", "2022-01-03"}
    row = lists["stocks_a"][1]
    assert row["ticker"] == "T2.US" and row["note"] == "brak danych EPS" and row["per_episode"] == []
    assert "pokonał S&P 500" in row["why"]
    assert lists["etf_a"][0]["ucits"] == "XYZ.LSE (0.97)" and lists["etf_b"][0]["ucits"] is None
    assert lists["stocks_b"][0]["alpha_sox"] == 0.1


def test_funnel_has_rejected_and_passed_pe_tables(wyniki):
    f = build_payloads(wyniki, wyniki / "metryki.csv")["funnel"]
    assert f["pe_rejected"] == [{"reason": "ujemny zysk (EPS)", "n": 2}] and f["pe_passed"][0]["n"] == 5


def test_missing_values_are_null_not_nan(wyniki):
    json.dumps(build_payloads(wyniki, wyniki / "metryki.csv"), allow_nan=False)
    rows = build_payloads(wyniki, wyniki / "metryki.csv")["episodes"]["rows"]
    assert [r for r in rows if r["episode_id"] == "2022-01-03"][0]["days_to_recovery"] is None


def test_no_secrets_in_payloads(wyniki):
    text = json.dumps(build_payloads(wyniki, wyniki / "metryki.csv"), ensure_ascii=False).lower()
    for bad in ("postgresql://", "password", "api_key"):
        assert bad not in text
    for var in ("PG_DSN", "EODHD_API_KEY", "FMP_API_KEY"):
        val = os.environ.get(var)
        if val:
            assert val.lower() not in text


@pytest.mark.db
def test_series_payload_shape():
    s = series_payload(twin_ids=["1973-01-11", "2022-01-03"], twin_peaks=["1973-01-11", "2022-01-03"],
                       last_ath="2026-10-06", as_of="2026-10-26")
    dates = [d for d, _ in s["sp500"]]
    assert len(dates) > 3000 and dates == sorted(dates) and dates[0] < "1930" and dates[-1] <= "2026-10-26"
    assert len(s["twins"]) == 2 and s["twins"][0]["path"][0] == [0, 100.0]
    assert s["today"]["path"][0] == [0, 100.0] and len(s["sox"]) > 500


def test_lists_rows_carry_rank_in_ranking_order(wyniki):
    lists = build_payloads(wyniki, wyniki / "metryki.csv")["lists"]
    assert [r["rank"] for r in lists["stocks_a"]] == [1, 2]
