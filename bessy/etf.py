"""Mapa sektorow, kandydaci ETF i odpowiedniki UCITS."""
import re

import numpy as np
import pandas as pd

SECTOR_INDEX = {
    "Technology": "SPLRCT.INDX", "Energy": "SPNY.INDX", "Utilities": "SPLRCU.INDX",
    "Consumer Defensive": "SPLRCS.INDX", "Consumer Cyclical": "SPLRCD.INDX", "Industrials": "SPLRCI.INDX",
    "Basic Materials": "SPLRCM.INDX", "Financial Services": "SPSY.INDX", "Healthcare": "SP500-35.INDX",
    "Communication Services": "SP500-50.INDX", "Real Estate": "XLRE.US",
}

EXCLUDE_PATTERNS = (
    r"\bshort\b(?![- ](term|duration|treasury|maturity|municipal))", r"(?<=[0-9a-z])short\b(?!-?term)",
    r"\binverse\b", r"\binvers[eoa]\b", r"apalanc", r"\bdoble\b", r"gehebelt", r"\blevier\b", r"\bbear\b", r"\bbull\b", r"\bultra(short|pro)?\b(?![- ]short[- ]term)(?! short bond)",
    r"leverage", r"(?<![a-z])short(?!term|duration|maturity)[a-z]{2,}", r"(?<![a-z0-9.])-?\d(\.\d+)?x\b", r"\bx[23]\b",
    r"(?<!low )(?<!lower )(?<!minimum )(?<!min )(?<!managed )(?<!risk )volatil", r"\bvix\b", r"vstoxx",
    r"yield index", r"treasury bill", r"interest rate", r"dollar (currency )?index", r"\bbullish\b", r"\bbearish\b", r"tail risk",
)
_EXCLUDE = re.compile("|".join(f"(?:{p})" for p in EXCLUDE_PATTERNS), re.IGNORECASE)


def is_excluded(name: str, ticker: str) -> bool:
    return bool(_EXCLUDE.search(f"{name or ''} {ticker or ''}"))


def etf_universe(instruments: pd.DataFrame) -> pd.DataFrame:
    d = instruments[instruments["kind"].isin(["etf", "index"])]
    keep = [not is_excluded(n, t) for n, t in zip(d["name"], d["ref_ticker"])]
    return d[keep].reset_index(drop=True)


def ucits_matches(us_w: pd.Series, eu_w: pd.DataFrame, min_corr: float = 0.95, min_weeks: int = 104,
                  top: int = 3, window_weeks: int = 156, horizon: int = 1,
                  vol_ratio: tuple = (0.7, 1.4)) -> pd.DataFrame:
    """Odpowiedniki: kolumny `eu_w` skorelowane z `us_w` (tygodniowe zwroty w USD, ostatnie 156 tygodni).

    `vol_ratio` odrzuca fundusze o zmiennosci zbyt innej niz oryginal. `horizon` > 1 liczy korelacje na zwrotach skumulowanych z tylu tygodni (kroczace): rozne godziny zamkniecia
    gield USA i Europy oraz kurs walutowy obnizaja korelacje tygodniowa nawet dla tego samego indeksu.
    """
    us = us_w.tail(window_weeks)
    eu = eu_w.reindex(us.index)
    if horizon > 1:
        us = np.expm1(np.log1p(us).rolling(horizon).sum())
        eu = np.expm1(np.log1p(eu).rolling(horizon).sum())
    n_weeks = eu.notna().mul(us.notna(), axis=0).sum()
    corr = eu.corrwith(us, min_periods=min_weeks)
    out = pd.DataFrame({"instrument_id": corr.index, "corr": corr.to_numpy(float), "n_weeks": n_weeks.reindex(corr.index).to_numpy()})
    out = out[out["n_weeks"] >= min_weeks]
    # zbyt rozna zmiennosc = inna strategia (np. covered call, bufor) mimo wysokiej korelacji z rynkiem
    ratio = (eu.std() / us.std()).reindex(out["instrument_id"]).to_numpy()
    out = out[(ratio >= vol_ratio[0]) & (ratio <= vol_ratio[1])]
    return out[out["corr"] >= min_corr].sort_values("corr", ascending=False).head(top).reset_index(drop=True)


def sector_table(metrics: pd.DataFrame, instruments: pd.DataFrame, episode_ids: list[str]) -> pd.DataFrame:
    """Zachowanie sektorow (indeksy S&P 500) w podanych okresach: alfa, odsetek wygranych, drawdown."""
    tick = instruments.set_index("instrument_id")["ref_ticker"]
    m = metrics[metrics["valid"] & metrics["episode_id"].isin(episode_ids)].copy()
    m["ticker"] = m["instrument_id"].map(tick)
    rows = []
    for sector, t in SECTOR_INDEX.items():
        s = m[m["ticker"] == t]
        if len(s):
            rows.append(dict(sector=sector, ticker=t, n_episodes=len(s), med_alpha=s["alpha"].median(),
                             win_rate=float((s["alpha"] > 0).mean()), med_ret=s["ret"].median(),
                             med_max_dd=s["max_dd"].median()))
    return pd.DataFrame(rows, columns=["sector", "ticker", "n_episodes", "med_alpha", "win_rate", "med_ret", "med_max_dd"])


_FUND_NAME = re.compile(r"\b(fund|portfolio|investment (company|trust)|income trust|trust (plc|ltd|limited)|"
                        r"macro limited|capital gearing|ruffer|closed[- ]end)\b|\btrust$", re.IGNORECASE)
_FOREIGN_LINE = re.compile(r"^0[A-Z0-9]{3}\.LSE$")


def is_fund_like(name: str, industry: str | None, ticker: str) -> bool:
    """Fundusze zamkniete, trusty inwestycyjne, spolki-wydmuszki i zagraniczne linie LSE (0xxx) nie sa spolkami operacyjnymi."""
    if _FOREIGN_LINE.match(ticker or ""):
        return True
    if industry == "Shell Companies":
        return True
    n = name or ""
    if re.search(r"\b(bank|corporation|corp|inc)\b", n, re.IGNORECASE) and not re.search(r"\b(fund|portfolio)\b", n, re.IGNORECASE):
        return False
    return bool(_FUND_NAME.search(n))


_BONDS = re.compile(r"\b(t-?bills?|treasur(y|ies)|bonds?|notes?|gilts?|bund|aggregate|floating|money market|overnight|"
                    r"ultra[- ]short|short[- ](term|duration|maturity)|preferred|fallen angels|mortgage|muni(cipal)?|credit|tips|"
                    r"1-3|0-1|3-7|7-10|20\+|loans?|clo|mbs|cmbs|sukuk|high[- ]yield|junk|corporate|fixed income|debt|govies?|cash)\b|rate swap|low duration|bulletshares|ibonds", re.IGNORECASE)
_COMMOD = re.compile(r"\b(gold|silver|platinum|palladium|copper|bullion|commodit(y|ies)|crude|oil|brent|gas|soybean|wheat|corn|"
                     r"agricultur(e|al)|currencyshares|yen|currency|bitcoin|ether)\b", re.IGNORECASE)
_ALT = re.compile(r"market neutral|anti-beta|tail risk|managed futures|long/short|hedge fund|hedged equity|equity hedge|volatility hedged|alternative|merger|"
                  r"mlt-asst|dynmc|buffer|defined (risk|outcome)|trendpilot|allocation|multi-asset|balanced|trinity|covered call|buywrite|"
                  r"\bincome (fund|etf)\b.*(option|premium)", re.IGNORECASE)
EQUITY_CORR = 0.55
INVERSE_CORR = -0.5
EU_ISIN_PREFIXES = ("IE", "LU", "DE", "FR", "NL", "AT", "ES", "IT", "BE", "SE", "FI", "DK")


def is_eu_domiciled(isin, ticker, name: str = "") -> bool:
    """ETF mozliwy do kupienia przez klienta z UE: ISIN z kraju UE (a bez ISIN: "UCITS" w nazwie) i prawdziwe
    notowanie (nie linia 0xxx.LSE)."""
    if _FOREIGN_LINE.match(ticker or ""):
        return False
    if isinstance(isin, str) and isin:
        return isin.startswith(EU_ISIN_PREFIXES)
    return "ucits" in (name or "").lower()
_MINERS = re.compile(r"\b(miners?|mining|royalty|streaming)\b", re.IGNORECASE)


def etf_class(name: str, corr: float | None = None) -> str:
    """Klasa funduszu: akcje / obligacje i inne / surowce i waluty / alternatywy.

    `corr` to korelacja tygodniowych zwrotow z S&P 500 TR (3 lata). Gdy znana, o akcjach decyduje zachowanie (>= 0,55).
    """
    n = name or ""
    if corr is not None and np.isfinite(corr) and corr < INVERSE_CORR:
        return "odwrotny"   # zachowuje sie odwrotnie do rynku (fundusz odwrotny, ochrona przed spadkiem)
    if _ALT.search(n):
        return "alternatywy"
    if _MINERS.search(n) or (_COMMOD.search(n) and not _BONDS.search(n)):
        return "surowce i waluty"
    if _BONDS.search(n):
        return "obligacje i inne"
    if corr is not None and np.isfinite(corr):
        return "akcje" if corr >= EQUITY_CORR else "obligacje i inne"
    return "obligacje i inne" if _BONDS.search(n) else "akcje"


def dedupe_by_correlation(ordered_ids: list, weekly: pd.DataFrame, threshold: float = 0.97) -> list:
    """Zachowuje pierwszy z kazdej grupy niemal identycznych funduszy (korelacja tygodniowych zwrotow >= prog)."""
    kept: list = []
    for i in ordered_ids:
        if i not in weekly:
            kept.append(i)
            continue
        dup = False
        for k in kept:
            if k in weekly:
                pair = weekly[[i, k]].dropna()
                if len(pair) >= 52 and pair[i].corr(pair[k]) >= threshold:
                    dup = True
                    break
        if not dup:
            kept.append(i)
    return kept
