"""Uruchomienie calego badania: python -m bessy.run --as-of 2026-10-26 --out ../../notatki/bessy_odpornosc_2026-11-03.md"""
import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from . import pipeline as P
from .db import index_series
from .etf import sector_table
from .macro import midterm_seasonality, pick_twins
from .panel import CACHE, fx_table, instruments
from .report import fp, fpp, f2, render_report
from .scoring import aggregate
from .serialize import to_jsonable

warnings.filterwarnings("ignore")
MONTHS = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]
WYNIKI = Path(__file__).resolve().parents[1] / "wyniki"


def stage(name: str, builder, refresh: bool) -> pd.DataFrame:
    return P.cached(name, builder, refresh)


def twin_text(twins: pd.DataFrame, cur: dict) -> str:
    lines = []
    for r in twins.itertuples():
        f = []
        if r.oil_shock:
            f.append(f"szok naftowy (ropa do {fp(r.oil_12m_max, 0)} w 12 mies.)")
        if r.tech_hot:
            f.append(f"przegrzanie technologii (Nasdaq/S&P {fp(r.tech_rs_24m, 0)} w 24 mies.)")
        if r.midterm:
            f.append("rok wyborów połówkowych")
        lines.append(f"- **{r.episode_id}** ({r.kind}, {fp(r.depth)}, dołek {r.trough_date:%Y-%m-%d}): " + ", ".join(f)
                     + f". Odległość od dzisiejszego układu: {f2(r.distance)}.")
    return "\n".join(lines) + ("\n\nUwaga: o wyborze decyduje odległość w przestrzeni trzech czynników, a nie podobieństwo przebiegu. "
                               "Korekty (jak 2010 i 2018) mają krótsze okna, więc ich wyniki są bardziej losowe niż wyniki prawdziwych bess.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2026-10-26")
    ap.add_argument("--out", default="../../notatki/bessy_odpornosc_2026-11-03.md")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    asof, refresh = a.as_of, a.refresh
    WYNIKI.mkdir(exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    fx = fx_table()
    spxtr, gspc = index_series("SPXTR.INDX"), index_series("GSPC.INDX")

    print("1/9 makro, bliźniaki")
    ep, flags, cur, twins = P.macro_stage(asof)
    epA = ep[ep["peak_date"] >= P.A_MIN_PEAK].reset_index(drop=True)
    ids_a, ids_b = list(epA["episode_id"]), list(twins["episode_id"])

    print("2/9 płynność i kandydaci")
    liq = stage(f"liquidity_{asof}", lambda: P.recent_liquidity(asof, fx), refresh)
    ins = instruments().merge(liq, on="instrument_id", how="left")
    cand = P.candidate_ids(ins)

    print("3/9 metryki wszystkich okresów")
    m = P.build_metrics(epA, set(cand["instrument_id"]), fx, spxtr, gspc, refresh)

    print("4/9 beta, trend")
    beta_a = stage("betaA", lambda: P.group_beta(ids_a).to_frame("b"), refresh)["b"]
    beta_b = stage("betaB4", lambda: P.group_beta(ids_b).to_frame("b"), refresh)["b"]
    trend = stage("trend", lambda: P.trend_stage(asof, set(cand["instrument_id"]), fx, spxtr)[0], refresh)

    print("5/9 P/E kandydatów")
    st = cand[cand["kind"] == "stock"]
    ms = m[m["instrument_id"].isin(set(st["instrument_id"]))]
    aa, ab = aggregate(ms, ids_a), aggregate(ms, ids_b)
    pool = sorted(set(aa[(aa.n_valid >= 4) & (aa.win_rate >= .7)]["instrument_id"]) | set(ab[(ab.n_valid >= 2) & (ab.win_rate >= .7)]["instrument_id"]))
    pe = stage("pe_status", lambda: P.pe_stage(pool, ins, asof, fx), refresh)
    if "instrument_id" in pe.columns:
        pe = pe.set_index("instrument_id")

    print("6/9 rankingi spółek i ETF")
    stocks = P.stock_rankings(ins, cand, m, trend, pe, beta_a, beta_b, epA, ids_b, spxtr, gspc)
    if refresh or not all((CACHE / f"etf_{k}.parquet").exists() for k in ("A", "B")):
        for k, v in P.etf_stage(asof, ins, cand, m, trend, beta_a, beta_b, ids_a, ids_b, fx, spxtr).items():
            v.to_parquet(CACHE / f"etf_{k}.parquet")
    etfs = {k: pd.read_parquet(CACHE / f"etf_{k}.parquet") for k in ("A", "B")}

    print("7/9 sektory i P/E sektorów")
    allm = stage("sector_pe_stocks", P.sector_pe_stage, refresh)
    spe = P.aggregate_sector_pe(allm)
    pe_sum = P.sector_pe_summary(spe, ep, asof)
    sec_a = sector_table(m, ins, ids_a)
    sec_b = sector_table(m, ins, ids_b)

    print("8/9 stan rynku, sezonowość, walidacja")
    state = P.state_stage(asof)
    seas_m, seas_p = midterm_seasonality(gspc)
    stocks_ids = set(st["instrument_id"])
    train = list(epA[epA["peak_date"] < "2015-01-01"]["episode_id"])
    test = list(epA[epA["peak_date"] >= "2015-01-01"]["episode_id"])
    oos = P.oos_test(m, stocks_ids, train, test)
    ids7 = list(pick_twins(flags, cur, k_max=99)["episode_id"])
    beta7 = stage("betaB7", lambda: P.group_beta(ids7).to_frame("b"), refresh)["b"]
    sens = P.sensitivity_stage(ins, cand, m, trend, pe, beta_b, beta7, ids_b, ids7)

    print("9/9 raport")
    ctx = build_context(asof, ep, flags, cur, twins, epA, state, seas_m, seas_p, sec_a, sec_b, pe_sum, stocks, etfs, oos, sens, m, stocks_ids)
    kontekst = dict(ctx=ctx, oos=oos, sens=sens, kolejnosc_a=ids_a, kolejnosc_b=ids_b,
                    lejek=P.funnel_steps(ins, cand, aa, pe, len(stocks["A"])), pe_tabele=P.pe_reason_tables(aa, pe))
    (WYNIKI / "kontekst.json").write_text(json.dumps(to_jsonable(kontekst), allow_nan=False, ensure_ascii=False), encoding="utf-8")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(ctx), encoding="utf-8")
    for name, df in {"epizody": flags, "czynniki": flags, "blizniaki": twins, "stan": state["indeksy"], "sektory_a": sec_a,
                     "sektory_b": sec_b, "sektory_pe": pe_sum, "sektory_pe_miesiecznie": spe,
                     "ranking_a_spolki": stocks["A"], "ranking_b_spolki": stocks["B"], "ranking_a_etf": etfs["A"],
                     "ranking_b_etf": etfs["B"], "pe_status": pe.reset_index()}.items():
        df.to_csv(WYNIKI / f"{name}.csv", index=False)
    m.to_csv(WYNIKI / "metryki.csv.gz", index=False)
    print("gotowe:", out)


def build_context(asof, ep, flags, cur, twins, epA, state, seas_m, seas_p, sec_a, sec_b, pe_sum, stocks, etfs, oos, sens, m, stocks_ids):
    ind = state["indeksy"]
    sp = ind[ind.ticker == "GSPC.INDX"].iloc[0]
    sox = ind[ind.ticker == "SOX.INDX"].iloc[0]
    tw_ids = list(twins["episode_id"])
    summary = (
        f"S&P 500 jest {fp(-sp.od_ath)} poniżej szczytu z {sp.data_ath:%Y-%m-%d}, więc szeroki rynek nie jest w bessie. "
        f"Z czterech czynników z briefu aktywne są dwa: ropa (indeks Brent {'+' if cur['oil_12m'] > 0 else ''}{fp(cur['oil_12m'], 0)} w 12 mies., próg szoku +40%) "
        f"i rok wyborów połówkowych (3.11.2026). Czynnik technologiczny jest rozdwojony: Nasdaq nie przewyższa S&P 500 o próg +15% "
        f"w 24 mies. (dziś {fp(cur['tech_rs_24m'], 0)}), ale półprzewodniki (SOX) są {fp(-sox.od_ath)} pod szczytem z {sox.data_ath:%Y-%m-%d}. "
        f"Spadki szerokich indeksów nie spełniają progu 15%. Najbliższe historyczne analogie według odległości w trzech czynnikach: "
        + ", ".join(tw_ids) + ".\n")
    rs = state["sila_relatywna"]
    conc = state["koncentracja"].iloc[0]
    state_text = (f"Siła relatywna: SOX/S&P 500 jest {fp(-rs.iloc[0].wzgledem_sp500_od_maks)} poniżej maksimum z {rs.iloc[0].data_maks:%Y-%m-%d}, "
                  f"a Nasdaq 100/S&P 500 {fp(-rs.iloc[1].wzgledem_sp500_od_maks)}. Koncentracja (S&P 500 do S&P 500 równoważonego) jest na {f2(conc.percentyl_historii, 0)}. "
                  f"percentylu historii od 1990, {fp(-conc.od_maks, 0)} poniżej maksimum z {conc.data_maks:%Y-%m-%d} i {fpp(conc.zmiana_5l, 0).replace(' pp','%')} w 5 lat. "
                  "Energia jest na historycznym maksimum, a Brent kosztuje o około 44% więcej niż trzy miesiące temu.\n")
    cz = [dict(okres="Dziś", ropa=cur["oil_12m"], tech=cur["tech_rs_24m"], wybory="tak", czynniki=np.nan, odleglosc=0.0)]
    for r in twins.itertuples():
        cz.append(dict(okres=r.episode_id, ropa=r.oil_12m_max, tech=r.tech_rs_24m, wybory="tak" if r.midterm else "nie",
                       czynniki=r.n_factors, odleglosc=r.distance))
    smm = seas_m.copy()
    smm["miesiac"] = [MONTHS[i - 1] for i in smm["month"]]
    post = seas_p.copy()
    done = post.dropna(subset=["r12m"])
    avg = pd.DataFrame([dict(year="średnia", election_date=pd.NaT, r3m=done.r3m.mean(), r6m=done.r6m.mean(), r12m=done.r12m.mean())])
    post_tab = pd.concat([post, avg], ignore_index=True)
    post_text = (f"Po dniu wyborów połówkowych S&P 500 średnio rósł {fp(done.r3m.mean())} w 3, {fp(done.r6m.mean())} w 6 i {fp(done.r12m.mean())} w 12 miesięcy "
                 f"(n = {len(done)}), a w {int((done.r12m > 0).sum())} z {len(done)} lat był dodatni po roku. To mała próba i nie zastępuje analizy wyników.\n")
    e = flags.copy()
    e["blizniak"] = np.where(e["episode_id"].isin(tw_ids), "tak", np.where((e["n_factors"] >= 2) & (e["peak_date"] >= "1970-01-01"), "kwalifikuje się", ""))
    e = e[e["peak_date"] >= "1946-01-01"]
    brief = e[(e["brief_match"] != "") & (e["peak_date"] >= "1970-01-01")]
    brief_text = ("\n".join(f"- {r.episode_id}: {r.brief_match}" for r in brief.itertuples()) or "Brak rozbieżności.") + \
        "\n\nProgi czynników ustalono przed liczeniem wyników spółek i nie zmieniano ich po obejrzeniu wyników. Okno ropy (od 365 dni przed szczytem do dołka) bywa " \
        "długie, więc przy długich bessach 2000 i 2010 czynnik ropy odzwierciedla odbicie po wcześniejszym dołku, a nie szok podażowy.\n"
    pe_text = ("P/E sektorów USA to suma kapitalizacji do sumy zysków TTM spółek o kapitalizacji co najmniej 2 mld EUR, tylko spółki z dodatnim zyskiem, "
               "P/E ograniczone do przedziału 3–250. Kolumna `Pokrycie` pokazuje, jaka część kapitalizacji sektora ma policzone P/E. "
               "Przy pokryciu poniżej 35% wynik jest orientacyjny. Szczyty i dołki to bessy od 2011 (EPS z SEC jest dostępny od około 2010).\n\n")
    ok = oos
    q = pd.DataFrame(ok["kwintyle"])
    valid_txt = (
        f"**Test poza próbą.** Ranking zbudowany wyłącznie na okresach do 2011 roku (13 okresów) sprawdziłem na okresach 2018, 2020, 2022 i 2025 "
        f"dla {fi_(ok['n'])} spółek. Korelacja rang wyniku z późniejszą alfą wynosi {f2(ok['spearman'])}. Najlepszy kwintyl miał medianę alfy "
        f"{fpp(q.iloc[-1]['test_med_alpha'])}, a najgorszy {fpp(q.iloc[0]['test_med_alpha'])}. Najlepszy decyl pokonywał S&P 500 w {fp(ok['top_decile_win'], 0)} okresów testowych "
        f"wobec {fp(ok['all_win'], 0)} dla wszystkich. Defensywność historyczna zatem częściowo się utrzymuje. Próba obejmuje tylko spółki notowane dziś, "
        f"co zawyża wyniki bezwzględne w obu częściach.\n\n")
    if sens:
        valid_txt += (f"**Wrażliwość na wybór bliźniaków.** Po zamianie czterech bliźniaków na wszystkie {len(sens['ids7'])} okresów kwalifikujących się (co najmniej dwa czynniki) "
                      f"{sens['overlap15']} z 15 spółek z listy „obecny układ” pozostaje na liście ({sens['overlap30']} z 30 w szerszym top 30). "
                      f"Stały trzon: {', '.join(sens['both'])}. Pozostałe pozycje zależą od doboru okresów, więc traktuj je jako mniej pewne.\n\n")
    valid_txt += ("**Waluty.** Wszystkie zwroty liczone są w USD. Dla spółek spoza USA obok alfy w USD widać alfę w walucie notowania w kodzie (`alpha_lokalna` w pliku CSV); "
                  "dla czołowych pozycji obie są zbliżone, więc przewaga nie wynika wyłącznie z kursu (na przykład franka).\n")
    zal = [
        "Dane: baza `marketdata`, ostatnie notowania 2026-10-26. Dostęp tylko do odczytu, żadne dane w bazie nie zostały zmienione.",
        "Benchmark: S&P 500 TR od 1988-02-08, wcześniej S&P 500 cenowy plus założone 4% rocznie z dywidend.",
        "Zwroty w USD na `adj_close`. Spółki spoza USA liczone tylko w okresach od 1999 roku (kursy walut w bazie od 1999-01-04).",
        "Próba spółek przed 1999 rokiem jest cienka (1973: ok. 40 ważnych instrumentów), więc wcześniejsze bessy mają mniejszą wagę dowodową.",
        "Okres ważny dla instrumentu: notowanie w ciągu 5 sesji od szczytu i do dołka (poza spółkami zdjętymi z giełdy), co najwyżej 20% dni bez zmiany ceny (liczonej w walucie notowania) lub z zerowym wolumenem, brak skoku danych (>50% cofniętego w 5 sesji).",
        "Ranking A: okresy ze szczytem od 1962 (17 okresów, w tym korekty), minimum 4 ważne okresy, co najmniej 70% wygranych. Kolumna `w tym bessy` pokazuje, ile z nich to prawdziwe bessy (spadek co najmniej 20%).",
        "Ranking B: bliźniacze bessy (4 okresy), minimum 3 ważne okresy (decyzja autora, plan dopuszczał 2) i co najmniej 70% wygranych, 75% wyniku z bliźniaków i 25% z bieżącego trendu (alfa od szczytu SOX i z 63 sesji).",
        "Wynik złożony to średnia percentyli: mediana alfy, odwrócona downside beta, mediana max DD, odsetek wygranych. Percentyle liczone w puli po wszystkich filtrach.",
        "Filtr P/E: odrzucone P/E powyżej 80. percentyla własnej historii (SEC, spółki w USD, minimum 60 miesięcy) i zysk TTM nieujemny. Bez historii albo bez danych EPS spółka przechodzi z uwagą w kolumnie `Uwagi`, więc taką pozycję sprawdź ręcznie.",
        "P/E z Yahoo (spółki spoza USA, ADR-y) to przybliżenie: brak historii, czasem tylko ostatni zysk roczny. EPS z SEC przeliczony na dzisiejszą bazę akcji (splity).",
        "Kupowalność: giełdy z listy XTB (US, LSE, XETRA, PA, AS, BR, MC, LS, SW, ST, CO, HE, OL, IR, WAR), mediana obrotu z 63 sesji co najmniej 1 mln USD, notowanie po 2026-10-20. To mój dobór, więc dostępność w XTB (zwłaszcza SW, ST, CO, HE, OL) sprawdź przed zakupem.",
        "Z list wyłączono fundusze zamknięte, trusty inwestycyjne i spółki-wydmuszki (heurystyka po nazwie i branży). Heurystyka może coś przepuścić lub odrzucić.",
        "ETF-y: klasa (akcje, obligacje i inne, surowce i waluty, alternatywy) wynika z nazw i korelacji z S&P 500 z 3 lat (akcje: co najmniej 0,55). Klasyfikacja jest heurystyczna. Fundusze o korelacji z S&P 500 poniżej −0,5 (zachowują się odwrotnie do rynku) są pomijane. Fundusze niemal identyczne (korelacja co najmniej 0,97) są zwinięte do jednego.",
        "Odpowiedniki UCITS: europejskie ETF-y z ISIN kraju UE (bez linii 0xxx.LSE, które są zagranicznymi funduszami), jeden na ISIN, o korelacji co najmniej 0,90 liczonej na kroczących 4-tygodniowych zwrotach w USD z ostatnich 3 lat (różne godziny zamknięcia giełd USA i Europy obniżają korelację tygodniową). ETF-y USA bez takiego odpowiednika wyłączono z list, bo nie kupisz ich w XTB. Wśród pozycji zaznaczonych jako notowane w Europie mogą być ETC (np. na złoto), które nie są UCITS. To podobieństwo zachowania, a nie ten sam indeks. Sprawdź indeks bazowy, koszty i dostępność w XTB.",
        "ETF-y obligacji i gotówki wygrywają w bessach z natury (alfa wobec S&P 500 to prawie samo uniknięcie spadku). Dlatego listy ETF są rozbite na klasy.",
        "Sezonowość wyborów połówkowych i analogie historyczne opierają się na kilkunastu zdarzeniach. To wskazówka, nie prognoza.",
    ]
    return dict(as_of=asof, podsumowanie=summary, stan=ind, stan_tekst=state_text, czynniki_teraz=pd.DataFrame(cz),
                sezonowosc_mies=smm, po_wyborach=post_tab, po_wyborach_tekst=post_text, epizody=e, blizniaki_tekst=twin_text(twins, cur),
                brief_tekst=brief_text, sektory_a=sec_a, sektory_b=sec_b, sektory_pe=pe_sum, sektory_pe_tekst=pe_text,
                top_a_spolki=stocks["A"], top_b_spolki=stocks["B"], top_a_etf=etfs["A"], top_b_etf=etfs["B"],
                walidacja=valid_txt, zalozenia=zal)


def fi_(x):
    return f"{int(x):,}".replace(",", " ")


if __name__ == "__main__":
    main()
