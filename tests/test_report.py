import numpy as np
import pandas as pd

from bessy.report import fp, fpp, md, render_report


def minimal_ctx():
    stock = pd.DataFrame([dict(ref_ticker="ED.US", name="Con Ed", sector="Utilities", exchange_code="US", n_valid=13, n_bessy=6,
                               med_alpha=0.268, downside_beta=0.55, med_max_dd=-0.12, win_rate=1.0, pe=19.5, pe_pct=70.0,
                               uwagi="", alpha_od_szczytu_sox=0.05, alpha_63d=0.01)])
    etf = pd.DataFrame([dict(classe="akcje", ref_ticker="USMV.US", name="Min Vol", exchange_code="US", currency="USD", n_valid=4,
                             med_alpha=0.1, downside_beta=0.7, med_max_dd=-0.15, win_rate=1.0, corr_spx=0.8,
                             odpowiedniki_ucits="MVOL.LSE (0.97)")])
    sect = pd.DataFrame([dict(sector="Energy", ticker="SPNY.INDX", n_episodes=5, med_alpha=0.1, win_rate=0.8, med_ret=-0.05, med_max_dd=-0.2)])
    return dict(as_of="2026-10-26",
                stan=pd.DataFrame([dict(indeks="S&P 500", data="2026-10-26", poziom=7676.8, od_ath=-0.018, data_ath="2026-10-06", r_3m=0.036, r_12m=0.13)]),
                czynniki_teraz=pd.DataFrame([dict(okres="Dziś", ropa=1.24, tech=0.07, wybory="tak", czynniki=2, odleglosc=0.0)]),
                sezonowosc_mies=pd.DataFrame([dict(miesiac="11", mean_wybory=0.03, median_wybory=0.02, mean_inne=0.01, median_inne=0.01)]),
                po_wyborach=pd.DataFrame([dict(year=2022, election_date="2022-11-08", r3m=0.1, r6m=0.05, r12m=0.12)]),
                epizody=pd.DataFrame([dict(episode_id="2022-01-03", trough_date="2022-10-12", kind="bessa", depth=-0.254, days_to_trough=282,
                                           recovery_date="2024-01-19", days_to_recovery=464, oil_12m_max=1.69, tech_rs_24m=0.18, midterm=True,
                                           n_factors=3, blizniak="tak")]),
                blizniaki_tekst="Tekst.", brief_tekst="Brak.", sektory_a=sect, sektory_b=sect,
                sektory_pe=pd.DataFrame([dict(sector="Energy", pe_teraz=16.7, med_5l=12.0, med_10l=15.0, perc_10l=60, vs_med_10l=0.1,
                                              pe_szczyt=15.0, pe_dolek=13.0, kompresja=-0.13, pokrycie=0.35, ocena="neutralny")]),
                top_a_spolki=stock, top_b_spolki=stock, top_a_etf=etf, top_b_etf=etf, zalozenia=["Założenie 1."])


def test_report_has_brief_sections_and_tables():
    txt = render_report(minimal_ctx())
    for h in ["## 1. Podsumowanie makro i historyczne analogie", "## 2. Wszystkie bessy i bessy podobne",
              "## 3. Mapa wycen sektorowych", "## 4. Spółki i ETF-y na każdą bessę",
              "## 5. Spółki i ETF-y na obecny układ", "## Założenia i ograniczenia"]:
        assert h in txt
    assert "| 2022-01-03 |" in txt and "| ED.US |" in txt and "MVOL.LSE (0.97)" in txt


def test_formatters_use_polish_decimal_comma_and_dash_for_nan():
    assert fp(0.1234) == "12,3%" and fpp(0.05) == "+5,0 pp" and fp(np.nan) == "–"
    assert md(pd.DataFrame({"a": [1.5]}), [("a", "A", lambda x: fp(x))]).splitlines()[2] == "| 150,0% |"
