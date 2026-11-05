"""Skladanie raportu Markdown (po polsku) z gotowych tabel."""
import numpy as np
import pandas as pd


def _num(x, d=1):
    return "–" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}".replace(".", ",")


def fp(x, d=1):
    return "–" if x is None or pd.isna(x) else _num(x * 100, d) + "%"


def fpp(x, d=1):
    return "–" if x is None or pd.isna(x) else ("+" if x > 0 else "") + _num(x * 100, d) + " pp"


def f2(x, d=2):
    return "–" if x is None or pd.isna(x) else _num(float(x), d)


def fd(x):
    return "–" if x is None or pd.isna(x) else pd.Timestamp(x).strftime("%Y-%m-%d")


def fi(x):
    return "–" if x is None or pd.isna(x) else f"{int(round(x)):,}".replace(",", " ")


def md(df: pd.DataFrame, cols: list[tuple]) -> str:
    """cols: (kolumna, naglowek, formatter|None)."""
    if df is None or len(df) == 0:
        return "_(brak danych)_\n"
    head = "| " + " | ".join(h for _, h, _ in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    rows = []
    for _, r in df.iterrows():
        cells = []
        for c, _, f in cols:
            v = r[c] if c in r.index else None
            cells.append((f(v) if f else ("–" if v is None or (not isinstance(v, str) and pd.isna(v)) else str(v))).replace("|", "/"))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep] + rows) + "\n"


def _why(r) -> str:
    wins = int(round(r["win_rate"] * r["n_valid"])) if pd.notna(r.get("win_rate")) else None
    parts = []
    if wins is not None:
        parts.append(f"pokonał S&P 500 w {wins}/{int(r['n_valid'])} okresach")
    parts.append(f"mediana alfy {fpp(r['med_alpha'], 0)}")
    parts.append(f"downside β {f2(r['downside_beta'])}")
    parts.append(f"mediana max DD {fp(r['med_max_dd'], 0)}")
    return ", ".join(parts)


STOCK_COLS = [("ref_ticker", "Ticker", None), ("name", "Nazwa", None), ("sector", "Sektor", None),
              ("exchange_code", "Giełda", None), ("n_valid", "Okresy", fi), ("n_bessy", "w tym bessy", fi),
              ("med_alpha", "Alfa (med.)", fpp), ("downside_beta", "Downside β", f2), ("med_max_dd", "Max DD (med.)", fp),
              ("win_rate", "Wygrane", lambda x: fp(x, 0)), ("pe", "P/E", lambda x: f2(x, 1)),
              ("pe_pct", "P/E perc.", lambda x: f2(x, 0)), ("uwagi", "Uwagi", None)]
STOCK_COLS_B = STOCK_COLS[:-1] + [("alpha_od_szczytu_sox", "Alfa od szczytu SOX", fpp), ("alpha_63d", "Alfa 63 sesje", fpp),
                                  ("uwagi", "Uwagi", None)]
ETF_COLS = [("classe", "Klasa", None), ("ref_ticker", "Ticker", None), ("name", "Nazwa", None),
            ("exchange_code", "Giełda", None), ("currency", "Waluta", None), ("n_valid", "Okresy", fi),
            ("med_alpha", "Alfa (med.)", fpp), ("downside_beta", "Downside β", f2), ("med_max_dd", "Max DD (med.)", fp),
            ("win_rate", "Wygrane", lambda x: fp(x, 0)), ("corr_spx", "Kor. z S&P", f2),
            ("odpowiedniki_ucits", "Odpowiedniki UCITS (korelacja)", None)]


why_text = _why


def _justify(df: pd.DataFrame) -> str:
    if df is None or len(df) == 0:
        return ""
    lines = [f"- **{r['ref_ticker']}** ({r['name']}): {_why(r)}." for _, r in df.iterrows()]
    return "\n".join(lines) + "\n"


def render_report(ctx: dict) -> str:
    c = ctx
    out = [f"# Odporność na bessę: spółki i ETF-y (dane do {c['as_of']})\n",
           "Analiza historyczna na bazie `marketdata` (tylko odczyt). Wynik to materiał do własnej weryfikacji, a nie rekomendacja. "
           "Przed zakupem sprawdź w XTB dostępność instrumentu, aktualną wycenę i ostatnie raporty spółki.\n"]
    out += ["## 1. Podsumowanie makro i historyczne analogie\n", c.get("podsumowanie", ""), "\n### Stan rynku\n",
            md(c["stan"], [("indeks", "Indeks", None), ("data", "Dzień", fd), ("poziom", "Poziom", lambda x: f2(x, 1)),
                           ("od_ath", "Od szczytu (ATH)", fp), ("data_ath", "Data ATH", fd), ("r_3m", "3 mies.", fp),
                           ("r_12m", "12 mies.", fp)]),
            "\n", c.get("stan_tekst", ""), "\n### Czynniki makro: dziś i w bliźniaczych bessach\n",
            md(c["czynniki_teraz"], [("okres", "Okres", None), ("ropa", "Ropa: największa zmiana 12-mies.", fp),
                                     ("tech", "Nasdaq/S&P 24 mies.", fp), ("wybory", "Wybory połówkowe", None),
                                     ("czynniki", "Czynniki", fi), ("odleglosc", "Odległość od dziś", f2)]),
            "\n### Sezonowość wyborów połówkowych (S&P 500 od 1950)\n",
            md(c["sezonowosc_mies"], [("miesiac", "Miesiąc", None), ("mean_wybory", "Średnia (rok wyborów)", fp),
                                      ("median_wybory", "Mediana (rok wyborów)", fp), ("mean_inne", "Średnia (pozostałe lata)", fp),
                                      ("median_inne", "Mediana (pozostałe lata)", fp)]),
            "\nZwrot S&P 500 po dniu wyborów połówkowych:\n\n",
            md(c["po_wyborach"], [("year", "Rok", None), ("election_date", "Dzień wyborów", fd), ("r3m", "3 mies.", fp),
                                  ("r6m", "6 mies.", fp), ("r12m", "12 mies.", fp)]), "\n", c.get("po_wyborach_tekst", "")]
    out += ["\n## 2. Wszystkie bessy i bessy podobne\n",
            "Bessa to spadek co najmniej 20% od szczytu, korekta to 15–20%. Zygzak: szczyt potwierdza spadek o 15%, dołek wzrost o 30% albo powrót na szczyt.\n\n",
            md(c["epizody"], [("episode_id", "Szczyt", None), ("trough_date", "Dołek", fd), ("kind", "Rodzaj", None),
                              ("depth", "Spadek", fp), ("days_to_trough", "Dni do dołka", fi), ("recovery_date", "Powrót na szczyt", fd),
                              ("days_to_recovery", "Dni od dołka do powrotu", fi), ("oil_12m_max", "Ropa 12 mies.", fp),
                              ("tech_rs_24m", "Tech 24 mies.", fp), ("midterm", "Wybory", lambda x: "tak" if x else "nie"),
                              ("n_factors", "Czynniki", fi), ("blizniak", "Bliźniak", None)]),
            "\n### Bliźniacze bessy\n", c["blizniaki_tekst"],
            "\n### Rozbieżności z oznaczeniami z briefu\n", c["brief_tekst"]]
    out += ["\n## 3. Mapa wycen sektorowych\n",
            "Zachowanie sektorów (indeksy sektorowe S&P 500) w bessach i w bliźniaczych bessach. Alfa liczona względem S&P 500 TR.\n\n",
            "**Wszystkie okresy od 1962:**\n\n", md(c["sektory_a"], SECT_COLS), "\n**Bliźniacze bessy:**\n\n", md(c["sektory_b"], SECT_COLS),
            "\n### P/E sektorów USA\n", c.get("sektory_pe_tekst", ""), md(c["sektory_pe"], PE_COLS)]
    out += ["\n## 4. Spółki i ETF-y na każdą bessę (wszystkie okresy)\n", "\n### Spółki\n",
            md(c["top_a_spolki"], STOCK_COLS), "\nUzasadnienie:\n\n", _justify(c["top_a_spolki"]),
            "\n### ETF-y\n", md(c["top_a_etf"], ETF_COLS)]
    out += ["\n## 5. Spółki i ETF-y na obecny układ (bliźniacze bessy i bieżący trend)\n", "\n### Spółki\n",
            md(c["top_b_spolki"], STOCK_COLS_B), "\nUzasadnienie:\n\n", _justify(c["top_b_spolki"]),
            "\n### ETF-y\n", md(c["top_b_etf"], ETF_COLS)]
    out += ["\n## 6. Czy metoda działa? Walidacja i odporność\n", c.get("walidacja", "")]
    out += ["\n## Założenia i ograniczenia\n", "\n".join(f"- {z}" for z in c["zalozenia"]) + "\n"]
    return "\n".join(out)


SECT_COLS = [("sector", "Sektor", None), ("ticker", "Indeks", None), ("n_episodes", "Okresy", fi),
             ("med_alpha", "Alfa (med.)", fpp), ("win_rate", "Wygrane", lambda x: fp(x, 0)),
             ("med_ret", "Zwrot (med.)", fp), ("med_max_dd", "Max DD (med.)", fp)]
PE_COLS = [("sector", "Sektor", None), ("pe_teraz", "P/E dziś", lambda x: f2(x, 1)), ("med_5l", "Mediana 5 lat", lambda x: f2(x, 1)),
           ("med_10l", "Mediana 10 lat", lambda x: f2(x, 1)), ("perc_10l", "Percentyl (10 lat)", lambda x: f2(x, 0)),
           ("vs_med_10l", "Wobec mediany 10 l.", fp), ("pe_szczyt", "P/E na szczytach bess (śr.)", lambda x: f2(x, 1)),
           ("pe_dolek", "P/E w dołkach bess (śr.)", lambda x: f2(x, 1)), ("kompresja", "Kompresja szczyt→dołek", fp),
           ("pokrycie", "Pokrycie kap.", lambda x: fp(x, 0)), ("ocena", "Ocena", None)]
