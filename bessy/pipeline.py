"""Etapy badania: uruchamiane przez bessy.run, wyniki posrednie w cache/ (parquet)."""
from pathlib import Path

import numpy as np
import pandas as pd

from .db import index_series, query_df
from .episodes import find_episodes
from .macro import current_state, macro_flags, oil_proxy, pick_twins
from .metrics import bench_return, bench_weekly_returns, downside_beta, episode_metrics, weekly_returns
from .panel import CACHE, fx_table, instruments, load_window, to_usd

A_MIN_PEAK = pd.Timestamp("1962-01-02")


def cached(name: str, builder, refresh: bool = False) -> pd.DataFrame:
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{name}.parquet"
    if f.exists() and not refresh:
        return pd.read_parquet(f)
    df = builder()
    df.to_parquet(f)
    return df


def macro_stage(as_of: str):
    gspc, ixic = index_series("GSPC.INDX"), index_series("IXIC.INDX")
    oil = oil_proxy(index_series("BCOMCO.INDX"), index_series("SPGSCI.INDX"))
    ep = find_episodes(gspc)
    flags = macro_flags(ep, oil, ixic, gspc)
    cur = current_state(oil, ixic, gspc, as_of)
    twins = pick_twins(flags, cur)
    return ep, flags, cur, twins


def recent_liquidity(as_of: str, fx: pd.DataFrame, sessions: int = 63) -> pd.DataFrame:
    """Mediana dziennego obrotu w USD z ostatnich `sessions` sesji."""
    end = pd.Timestamp(as_of)
    w = load_window(end - pd.Timedelta(days=110), end)
    p = to_usd(w, fx)
    days = np.sort(p["date"].unique())[-sessions:]
    p = p[p["date"].isin(days)]
    g = p.groupby("instrument_id")
    return pd.DataFrame({"turnover_usd": g["turnover_usd"].median(), "n_recent": g.size()}).reset_index()


def candidate_ids(ins: pd.DataFrame, etf_min_turnover: float = 2e5) -> pd.DataFrame:
    """Instrumenty, ktore moga trafic do rankingow: kupowalne spolki + ETF-y/indeksy bez produktow lewarowanych itp."""
    from .etf import etf_universe, is_fund_like
    from .scoring import purchasable
    st = ins[ins["kind"] == "stock"]
    st = st[[not is_fund_like(n, i, t) for n, i, t in zip(st["name"], st["industry"], st["ref_ticker"])]]
    stocks = purchasable(st)
    from .scoring import XTB_EXCHANGES
    etfs = etf_universe(ins)
    idx = etfs[etfs["kind"] == "index"]
    e = etfs[(etfs["kind"] == "etf") & (etfs["turnover_usd"] >= etf_min_turnover) & etfs["exchange_code"].isin(XTB_EXCHANGES)
             & ~etfs["is_delisted"].astype(bool)].sort_values("turnover_usd", ascending=False)
    e = pd.concat([e[e["isin"].notna()].drop_duplicates("isin"), e[e["isin"].isna()]])
    etfs = pd.concat([idx, e], ignore_index=True)
    return pd.concat([stocks, etfs], ignore_index=True)


QUALITY_PAD_DAYS = 10


def mask_invalid_weeks(wk: pd.DataFrame, metrics: pd.DataFrame, episode_id: str) -> pd.DataFrame:
    """Zeruje (NaN) tygodniowe zwroty instrumentow, ktorych okres jest nieważny (nie wchodza do downside beta)."""
    bad = {str(i) for i in metrics.loc[(metrics["episode_id"] == episode_id) & ~metrics["valid"], "instrument_id"]}
    out = wk.copy()
    cols = [c for c in out.columns if str(c) in bad]
    out[cols] = np.nan
    return out


def sens_summary(top_a: list, top_b: list, n: int = 15) -> dict:
    """Czesc wspolna i roznice dwoch rankingow (pierwsze n pozycji)."""
    a, b = list(top_a)[:n], list(top_b)[:n]
    return {"overlap": len(set(a) & set(b)), "both": sorted(set(a) & set(b)), "only_a": sorted(set(a) - set(b)),
            "only_b": sorted(set(b) - set(a))}


def build_metrics(episodes: pd.DataFrame, cand_ids: set, fx: pd.DataFrame, spxtr: pd.Series, gspc: pd.Series,
                  refresh: bool = False) -> pd.DataFrame:
    """Metryki wszystkich instrumentow w kazdym okresie + tygodniowe zwroty kandydatow (cache/weekly_*.parquet)."""
    f = CACHE / "metrics_all.parquet"
    if f.exists() and not refresh:
        return pd.read_parquet(f)
    out = []
    for r in episodes.itertuples():
        pad = pd.Timedelta(days=QUALITY_PAD_DAYS)
        w = load_window(r.peak_date - pad, r.trough_date + pad)
        p = to_usd(w, fx)
        b = bench_return(spxtr, gspc, r.peak_date, r.trough_date)
        mm = episode_metrics(p, b, r.peak_date, r.trough_date, r.episode_id)
        out.append(mm)
        p = p[p["date"].between(r.peak_date, r.trough_date)]
        wk = weekly_returns(p[p["instrument_id"].isin(cand_ids)])
        wk = mask_invalid_weeks(wk, mm, r.episode_id)
        wk.columns = wk.columns.astype(str)
        wk["__bench__"] = bench_weekly_returns(spxtr, gspc, r.peak_date, r.trough_date).reindex(wk.index)
        wk.to_parquet(CACHE / f"weekly_{r.episode_id}.parquet")
        print(f"  {r.episode_id}: {len(w):>9,} wierszy, bench {b:+.3f}", flush=True)
    m = pd.concat(out, ignore_index=True)
    m.to_parquet(f)
    return m


def group_beta(episode_ids: list[str], min_weeks: int = 26) -> pd.Series:
    """Downside beta instrumentow z tygodni wszystkich podanych okresow (indeks: instrument_id jako int)."""
    frames = [pd.read_parquet(CACHE / f"weekly_{e}.parquet") for e in episode_ids]
    wk = pd.concat(frames, ignore_index=True)
    bench = wk.pop("__bench__")
    beta = downside_beta(wk, bench, min_weeks=min_weeks)
    beta.index = beta.index.astype(int)
    return beta


def window_alpha(start, end, ids, bench_ret: float, fx: pd.DataFrame, tol_days: int = 7) -> pd.Series:
    """Alfa instrumentow w oknie [start, end]; NaN, gdy brak notowan blisko obu koncow okna."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    p = to_usd(load_window(start, end), fx)
    p = p[p["instrument_id"].isin(ids)].dropna(subset=["px_usd"]).sort_values(["instrument_id", "date"])
    g = p.groupby("instrument_id")
    first_d, last_d = g["date"].first(), g["date"].last()
    ret = g["px_usd"].last() / g["px_usd"].first() - 1
    ok = (first_d - start <= pd.Timedelta(days=tol_days)) & (end - last_d <= pd.Timedelta(days=tol_days))
    return (ret - bench_ret).where(ok)


def trend_stage(as_of: str, ids, fx, spxtr: pd.Series, sessions: int = 63) -> tuple[pd.DataFrame, dict]:
    sox = index_series("SOX.INDX")
    sox = sox[sox.index <= pd.Timestamp(as_of)]
    sox_peak = sox.idxmax()
    days = spxtr.index[spxtr.index <= pd.Timestamp(as_of)]
    d63 = days[-sessions]
    out = pd.DataFrame({
        "alpha_od_szczytu_sox": window_alpha(sox_peak, as_of, ids, bench_return(spxtr, spxtr, sox_peak, as_of), fx),
        "alpha_63d": window_alpha(d63, as_of, ids, bench_return(spxtr, spxtr, d63, as_of), fx),
    })
    out.index.name = "instrument_id"
    info = {"sox_peak": sox_peak, "sox_dd": float(sox.iloc[-1] / sox.max() - 1), "d63": d63,
            "bench_sox": bench_return(spxtr, spxtr, sox_peak, as_of), "bench_63": bench_return(spxtr, spxtr, d63, as_of)}
    return out.reset_index(), info


def pe_stage(ids, ins: pd.DataFrame, as_of: str, fx: pd.DataFrame) -> pd.DataFrame:
    """P/E biezace i jego percentyl w wlasnej historii (SEC, tylko notowania w USD). Zapas: Yahoo (tylko biezace)."""
    from .valuation import eps_fx_ratio, pe_filter, pe_monthly, quarterly_eps, split_factor, ttm_eps
    ids = [int(i) for i in ids]
    as_of_ts = pd.Timestamp(as_of)
    eps = query_df("select f.instrument_id, f.source, f.period_type, f.period_end, f.value, f.currency, f.usable_from "
                   "from fundamental_statement f where f.instrument_id = any(%(i)s) and f.line_item = 'eps_diluted' "
                   "and f.status = 'ok'", {"i": ids})
    spl = query_df("select instrument_id, ex_date, ratio from split where instrument_id = any(%(i)s)", {"i": ids})
    spl["ex_date"], spl["ratio"] = pd.to_datetime(spl["ex_date"]), spl["ratio"].astype(float)
    mp = query_df("select instrument_id, date, close from monthly_price where instrument_id = any(%(i)s) "
                  "and date >= '2008-12-01' order by instrument_id, date", {"i": ids})
    mp["date"] = pd.to_datetime(mp["date"])
    last = query_df("select distinct on (instrument_id) instrument_id, date, close from daily_price "
                    "where instrument_id = any(%(i)s) and date <= %(d)s order by instrument_id, date desc",
                    {"i": ids, "d": as_of})
    last = last.set_index("instrument_id")
    cur_ccy = ins.set_index("instrument_id")["currency"]
    rows = []
    for iid in ids:
        sp = spl[spl["instrument_id"] == iid]
        e = eps[eps["instrument_id"] == iid]
        sec = e[e["source"] == "sec_edgar"]
        res = dict(instrument_id=iid, pe=np.nan, eps_ttm=np.nan, pe_source="", n_hist=0)
        px_now = float(last.loc[iid, "close"]) if iid in last.index else np.nan
        hist = pd.Series(dtype=float)
        if len(sec) and cur_ccy.get(iid) == "USD":
            q = quarterly_eps(sec, sp)
            res["eps_ttm"] = ttm_eps(q, as_of_ts)
            if np.isfinite(res["eps_ttm"]) and res["eps_ttm"] > 0 and np.isfinite(px_now):
                res["pe"] = px_now / split_factor(as_of_ts, sp) / res["eps_ttm"]
                res["pe_source"] = "SEC"
            m = mp[(mp["instrument_id"] == iid) & (mp["date"] < as_of_ts.replace(day=1))]
            hist = pe_monthly(pd.Series(m["close"].to_numpy(), index=m["date"]), q, sp)
        if not np.isfinite(res["eps_ttm"]):
            y = e[e["source"] == "yahoo"]
            if len(y) and np.isfinite(px_now):
                q = quarterly_eps(y[y["period_type"] == "quarterly"].assign(period_type="quarterly"), sp)
                t = ttm_eps(q, as_of_ts)
                if np.isfinite(t):
                    ccy = y["currency"].iloc[0]
                    ratio = eps_fx_ratio(ccy, cur_ccy.get(iid, ccy), as_of_ts, fx)
                    eps_loc = t * ratio if np.isfinite(ratio) else np.nan
                    res["eps_ttm"] = eps_loc
                    if np.isfinite(eps_loc) and eps_loc > 0:
                        res["pe"] = px_now / split_factor(as_of_ts, sp) / eps_loc
                        res["pe_source"] = "Yahoo"
        if not np.isfinite(res["eps_ttm"]) and len(e) and np.isfinite(px_now):
            # szczebel 4: ostatni roczny EPS (do 540 dni wstecz), tylko przyblizenie biezacego P/E
            an = e[(e["period_type"] == "annual") & (pd.to_datetime(e["usable_from"]) <= as_of_ts)]
            an = an[(as_of_ts - pd.to_datetime(an["period_end"])).dt.days <= 540].sort_values("period_end")
            if len(an):
                r = an.iloc[-1]
                ratio = 1.0 if r["source"] == "sec_edgar" else eps_fx_ratio(r["currency"], cur_ccy.get(iid, r["currency"]), as_of_ts, fx)
                v = float(r["value"]) / split_factor(r["usable_from"], sp) * ratio
                res["eps_ttm"], res["pe_source"] = v, "roczny"
                if v > 0 and np.isfinite(v):
                    res["pe"] = px_now / split_factor(as_of_ts, sp) / v
        ok, reason, pct = pe_filter(res["pe"], hist, eps_ttm=res["eps_ttm"])
        res.update(pe_pass=ok, pe_reason=reason, pe_pct=pct, n_hist=int(hist.notna().sum()))
        rows.append(res)
    return pd.DataFrame(rows).set_index("instrument_id")


ETF_TOP = {"akcje": 12, "obligacje i inne": 5, "surowce i waluty": 5, "alternatywy": 3}


def etf_stage(as_of: str, ins, cand, m, trend, beta_a, beta_b, ids_a, ids_b, fx, spxtr, weeks: int = 156) -> dict:
    """Rankingi ETF A i B w klasach (klasa z korelacji z S&P 500), bez duplikatow, z odpowiednikami UCITS."""
    from .etf import dedupe_by_correlation, etf_class, is_eu_domiciled, ucits_matches
    from .metrics import weekly_returns
    from .panel import load_prices
    from .scoring import aggregate, rank_a, rank_b
    etf = cand[cand["kind"] == "etf"].copy()
    end = pd.Timestamp(as_of)
    p = to_usd(load_prices(sorted(etf["instrument_id"]), end - pd.Timedelta(weeks=weeks + 4), end), fx)
    wk = weekly_returns(p).tail(weeks)
    wk.columns = wk.columns.astype(int)
    spx_w = spxtr.loc[wk.index[0] - pd.Timedelta(days=7):end].resample("W-FRI").last().pct_change().reindex(wk.index)
    corr = wk.corrwith(spx_w, min_periods=104)
    etf["corr_spx"] = etf["instrument_id"].map(corr)
    etf["classe"] = [etf_class(n, c if np.isfinite(c) else None) for n, c in zip(etf["name"], etf["corr_spx"])]
    me = m[m["instrument_id"].isin(set(etf["instrument_id"]))]
    ranks = {
        "A": rank_a(aggregate(me, ids_a), beta_a, etf, None, min_valid=3, top=10000, apply_purchasable=False),
        "B": rank_b(aggregate(me, ids_b), beta_b, trend, etf, None, min_valid=2, top=10000, apply_purchasable=False),
    }
    pool = ucits_pool(ins)
    pw = to_usd(load_prices(sorted(pool["instrument_id"]), end - pd.Timedelta(weeks=weeks + 4), end), fx)
    pwk = weekly_returns(pw).tail(weeks)
    pwk.columns = pwk.columns.astype(int)
    info = pd.concat([etf, pool]).drop_duplicates("instrument_id").set_index("instrument_id")
    out = {}
    for k, r in ranks.items():
        r = r.merge(etf[["instrument_id", "classe", "region", "currency", "turnover_usd", "corr_spx"]],
                    on="instrument_id", how="left")
        tables = []
        for cls, n in ETF_TOP.items():
            sub = r[r["classe"] == cls].head(80).copy()
            eq, mids = [], {}
            for _, row in sub.iterrows():
                iid = row["instrument_id"]
                if row["region"] == "eu":
                    eq.append("(notowany w Europie)" if is_eu_domiciled(row["isin"], info.loc[iid, "ref_ticker"], row["name"]) else None)
                elif iid in wk.columns:
                    mt = ucits_matches(wk[iid], pwk[[c for c in pwk.columns if c != iid]], min_corr=0.90, horizon=4)
                    mids[iid] = list(mt["instrument_id"])
                    eq.append("; ".join(f"{info.loc[i, 'ref_ticker']} ({c:.2f})" for i, c in zip(mt["instrument_id"], mt["corr"])) or None)
                else:
                    eq.append(None)
            sub["odpowiedniki_ucits"] = eq
            sub = sub[sub["odpowiedniki_ucits"].notna()]   # bez odpowiednika UCITS nie kupisz w XTB (cel: tylko UCITS)
            uniq = drop_equivalent_duplicates([(i, g, mids.get(i, [])) for i, g in zip(sub["instrument_id"], sub["region"])])
            keep = dedupe_by_correlation(uniq, wk, 0.97)[:n]
            order = {i: j for j, i in enumerate(keep)}
            tables.append(sub[sub["instrument_id"].isin(keep)].assign(_o=lambda d: d["instrument_id"].map(order)).sort_values("_o").drop(columns="_o"))
        out[k] = pd.concat(tables, ignore_index=True)
    return out


def drop_equivalent_duplicates(rows: list) -> list:
    """rows: (id, region, [id odpowiednikow UCITS]) w kolejnosci rankingu. Jedno miejsce na fundusz:
    pomija fundusz z UE, jesli jego odpowiednik USA jest juz na liscie, i odwrotnie."""
    keep, covered = [], set()
    for iid, region, matches in rows:
        if region == "eu":
            if iid in covered:
                continue
            covered.add(iid)
        else:
            if matches[0] in covered:
                continue
            covered.add(matches[0])
        keep.append(iid)
    return keep


def ucits_pool(ins: pd.DataFrame) -> pd.DataFrame:
    """Europejskie ETF-y mogace byc odpowiednikami: ISIN z UE, prawdziwe notowanie, jedno na ISIN (preferuj gieldy XTB, wiekszy obrot)."""
    from .etf import etf_universe, is_eu_domiciled
    from .scoring import XTB_EXCHANGES
    e = etf_universe(ins)
    e = e[(e["kind"] == "etf") & (e["region"] == "eu") & ~e["is_delisted"].astype(bool) & e["exchange_code"].isin(XTB_EXCHANGES)]
    e = e[[is_eu_domiciled(i, t, n) for i, t, n in zip(e["isin"], e["ref_ticker"], e["name"])]]
    e = e.assign(_x=e["exchange_code"].isin(XTB_EXCHANGES)).sort_values(["_x", "turnover_usd"], ascending=False)
    return e.drop_duplicates("isin").drop(columns="_x").reset_index(drop=True)


def sector_pe_stage(min_cap_eur: float = 2e9, since: str = "2009-12-01") -> pd.DataFrame:
    """Miesieczne P/E spolek USA (sektor Yahoo, kap. >= 2 mld EUR) z kapitalizacja PIT; agregacja: aggregate_sector_pe."""
    from .valuation import pe_monthly, quarterly_eps
    base = query_df(
        "select i.instrument_id, i.sector from instrument i join (select instrument_id, max(cap_eur) mc from cap_snapshot "
        "where source='pit_shares' group by 1) c using(instrument_id) join listing l on l.instrument_id=i.instrument_id and l.is_primary "
        "where i.kind='stock' and i.sector is not null and l.exchange_code='US' and i.currency='USD' and c.mc >= %(c)s",
        {"c": min_cap_eur})
    ids = [int(i) for i in base["instrument_id"]]
    eps = query_df("select instrument_id, period_type, period_end, value, usable_from from fundamental_statement "
                   "where instrument_id = any(%(i)s) and line_item='eps_diluted' and source='sec_edgar' and status='ok'", {"i": ids})
    spl = query_df("select instrument_id, ex_date, ratio from split where instrument_id = any(%(i)s)", {"i": ids})
    spl["ex_date"], spl["ratio"] = pd.to_datetime(spl["ex_date"]), spl["ratio"].astype(float)
    mp = query_df("select instrument_id, date, close from monthly_price where instrument_id = any(%(i)s) and date >= %(s)s",
                  {"i": ids, "s": since})
    mp["date"] = pd.to_datetime(mp["date"])
    cap = query_df("select instrument_id, as_of, cap_eur from cap_snapshot where instrument_id = any(%(i)s) "
                   "and source='pit_shares' and as_of >= %(s)s", {"i": ids, "s": since})
    cap["as_of"] = pd.to_datetime(cap["as_of"])
    g_eps, g_spl, g_mp = (dict(list(x.groupby("instrument_id"))) for x in (eps, spl, mp))
    rows = []
    for iid in ids:
        if iid not in g_eps or iid not in g_mp:
            continue
        q = quarterly_eps(g_eps[iid], g_spl.get(iid))
        m = g_mp[iid]
        pe = pe_monthly(pd.Series(m["close"].to_numpy(), index=m["date"]), q, g_spl.get(iid))
        rows.append(pd.DataFrame({"instrument_id": iid, "date": pe.index, "pe": pe.to_numpy()}))
    pes = pd.concat(rows, ignore_index=True)
    # tylko spolki z EPS z SEC (krajowi emitenci): ADR-y (formularz 20-F) nie maja kwartalnego EPS w bazie i zanizalyby pokrycie
    mp = mp[mp["instrument_id"].isin(g_eps)]
    allm = mp[["instrument_id", "date"]].merge(pes, on=["instrument_id", "date"], how="left")
    allm = allm.sort_values("date")
    allm = pd.merge_asof(allm, cap.sort_values("as_of").rename(columns={"as_of": "date"}), on="date", by="instrument_id",
                         tolerance=pd.Timedelta(days=10), direction="backward")
    allm = allm.merge(base, on="instrument_id")
    return allm


MAX_CAP_EUR = 6e12


def drop_cap_outliers(allm: pd.DataFrame, max_cap: float = MAX_CAP_EUR, band: tuple = (0.2, 5.0)) -> pd.DataFrame:
    """Usuwa bledne kapitalizacje: powyzej `max_cap` (np. kap. ADR w walucie lokalnej opisana jako EUR) i skoki
    poza pasmem wzgledem kroczacej mediany tego samego instrumentu."""
    d = allm.sort_values(["instrument_id", "date"]).copy()
    med = d.groupby("instrument_id")["cap_eur"].transform(lambda s: s.astype(float).rolling(12, min_periods=3, center=True).median())
    ratio = d["cap_eur"].astype(float) / med
    keep = (d["cap_eur"].astype(float) <= max_cap) & ~((ratio < band[0]) | (ratio > band[1]))
    return d[keep.fillna(True) & (d["cap_eur"].astype(float) <= max_cap)]


def aggregate_sector_pe(allm: pd.DataFrame, lo: float = 3.0, hi: float = 250.0) -> pd.DataFrame:
    """P/E sektora: ważone kapitalizacją (suma kap / suma zyskow) i mediana; tylko P/E w [lo, hi]. Pokrycie = udzial kap."""
    from .valuation import sector_pe
    d = drop_cap_outliers(allm.dropna(subset=["cap_eur"]))
    d["cap"] = d["cap_eur"].astype(float)
    ok = d[(d["pe"] >= lo) & (d["pe"] <= hi)]
    spe = sector_pe(ok)
    med = ok.groupby(["sector", "date"])["pe"].median().rename("pe_med").reset_index()
    n = ok.groupby(["sector", "date"]).size().rename("n").reset_index()
    cov = (ok.groupby(["sector", "date"])["cap"].sum() / d.groupby(["sector", "date"])["cap"].sum()).rename("pokrycie").reset_index()
    return spe.merge(med, on=["sector", "date"]).merge(n, on=["sector", "date"]).merge(cov, on=["sector", "date"])


def oos_test(m: pd.DataFrame, stock_ids: set, train_ids: list[str], test_ids: list[str], min_train: int = 3,
             min_test: int = 2) -> dict:
    """Test trwalosci: ranking zbudowany na okresach `train_ids`, ocena alfy na `test_ids` (kwintyle wyniku)."""
    from .scoring import aggregate
    ms = m[m["instrument_id"].isin(stock_ids)]
    tr, te = aggregate(ms, train_ids), aggregate(ms, test_ids)
    beta = group_beta(train_ids)
    tr["downside_beta"] = tr["instrument_id"].map(beta)
    tr = tr[(tr["n_valid"] >= min_train) & tr["downside_beta"].notna()].copy()
    tr["score"] = pd.concat([tr["med_alpha"].rank(pct=True), (-tr["downside_beta"]).rank(pct=True),
                             tr["med_max_dd"].rank(pct=True), tr["win_rate"].rank(pct=True)], axis=1).mean(axis=1)
    te = te[te["n_valid"] >= min_test][["instrument_id", "med_alpha", "win_rate", "med_max_dd"]].add_prefix("test_").rename(
        columns={"test_instrument_id": "instrument_id"})
    j = tr.merge(te, on="instrument_id")
    j["kwintyl"] = pd.qcut(j["score"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    q = j.groupby("kwintyl", observed=True).agg(n=("instrument_id", "size"), test_med_alpha=("test_med_alpha", "median"),
                                              test_win=("test_win_rate", "mean"), test_dd=("test_med_max_dd", "median"))
    top = j[j["score"] >= j["score"].quantile(0.9)]
    return {"n": len(j), "spearman": float(j["score"].rank().corr(j["test_med_alpha"].rank())),
            "kwintyle": q.reset_index(), "top_decile_alpha": float(top["test_med_alpha"].median()),
            "all_alpha": float(j["test_med_alpha"].median()), "top_decile_win": float(top["test_win_rate"].mean()),
            "all_win": float(j["test_win_rate"].mean())}


def local_alpha(ids, episodes: pd.DataFrame, spxtr: pd.Series, gspc: pd.Series, metrics: pd.DataFrame) -> pd.Series:
    """Mediana alfy w walucie notowania (bez efektu kursu) po tych samych okresach, co alfa w USD (tylko wazne)."""
    ids = set(int(i) for i in ids)
    valid = metrics[metrics["valid"] & metrics["instrument_id"].isin(ids)][["instrument_id", "episode_id"]]
    out = {}
    for r in episodes.itertuples():
        v = set(valid.loc[valid["episode_id"] == r.episode_id, "instrument_id"])
        w = load_window(r.peak_date, r.trough_date)
        w = w[w["instrument_id"].isin(v)].sort_values(["instrument_id", "date"])
        g = w.groupby("instrument_id")["adj_close"]
        out[r.episode_id] = (g.last() / g.first() - 1 - bench_return(spxtr, gspc, r.peak_date, r.trough_date))
    return pd.DataFrame(out).median(axis=1)


def bear_counts(ms: pd.DataFrame, episodes: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
    """Liczba prawdziwych bess (i odsetek wygranych w nich) wsrod okresow `ids` danego rankingu."""
    from .scoring import aggregate
    bears = list(episodes[(episodes["kind"] == "bessa") & episodes["episode_id"].isin(ids)]["episode_id"])
    return aggregate(ms, bears).rename(columns={"n_valid": "n_bessy", "win_rate": "win_bessy"})[
        ["instrument_id", "n_bessy", "win_bessy"]]


def stock_rankings(ins, cand, m, trend, pe, beta_a, beta_b, ep_a: pd.DataFrame, ids_b: list[str], spxtr, gspc,
                   top: int = 15, min_b: int = 3) -> dict:
    from .scoring import aggregate, rank_a, rank_b
    st = cand[cand["kind"] == "stock"]
    ms = m[m["instrument_id"].isin(set(st["instrument_id"]))]
    ids_a = list(ep_a["episode_id"])
    ra = rank_a(aggregate(ms, ids_a), beta_a, st, pe, min_valid=4, top=top)
    rb = rank_b(aggregate(ms, ids_b), beta_b, trend, st, pe, min_valid=min_b, top=top)
    cur = ins.set_index("instrument_id")["currency"]
    for name, r, eps in (("A", ra, ep_a), ("B", rb, ep_a[ep_a["episode_id"].isin(ids_b)])):
        r = r.merge(bear_counts(ms, ep_a, list(eps["episode_id"])), on="instrument_id", how="left")
        r["waluta"] = r["instrument_id"].map(cur)
        r["alpha_lokalna"] = r["instrument_id"].map(local_alpha(r["instrument_id"], eps, spxtr, gspc, ms))
        r = r.merge(pe[["pe", "pe_pct", "pe_reason", "pe_source"]].reset_index(), on="instrument_id", how="left", suffixes=("", "_pe"))
        if name == "A":
            ra = r
        else:
            rb = r
    return {"A": ra, "B": rb}


STATE_TICKERS = [("S&P 500", "GSPC.INDX"), ("Nasdaq 100", "NDX.INDX"), ("Półprzewodniki (SOX)", "SOX.INDX"),
                 ("S&P 500 Energy", "GSPE.INDX"), ("STOXX Europe 600", "SXXP.INDX"), ("WIG20", "WIG20.INDX"),
                 ("WIG", "WIG.INDX"), ("Brent (indeks BCOMCO)", "BCOMCO.INDX"), ("VIX", "VIX.INDX")]


def state_stage(as_of: str) -> dict:
    """Stan rynku: obsuniecie od ATH, zwroty 3 i 12 mies., siła relatywna SOX i NDX do S&P, koncentracja najwiekszych spolek USA."""
    end = pd.Timestamp(as_of)
    rows, series = [], {}
    for label, t in STATE_TICKERS:
        s = index_series(t)
        s = s[s.index <= end]
        series[t] = s
        ath_date = s.idxmax()
        def back(days):
            return float(s.iloc[-1] / s.asof(s.index[-1] - pd.Timedelta(days=days)) - 1)
        rows.append(dict(indeks=label, ticker=t, data=s.index[-1], poziom=float(s.iloc[-1]), ath=float(s.max()),
                         data_ath=ath_date, od_ath=float(s.iloc[-1] / s.max() - 1), r_3m=back(91), r_12m=back(365)))
    tbl = pd.DataFrame(rows)
    rs = []
    g = series["GSPC.INDX"]
    for label, t in (("Półprzewodniki (SOX)", "SOX.INDX"), ("Nasdaq 100", "NDX.INDX")):
        r = (series[t] / g).dropna()
        rs.append(dict(indeks=label, wzgledem_sp500_od_maks=float(r.iloc[-1] / r.max() - 1), data_maks=r.idxmax(),
                       zmiana_12m=float(r.iloc[-1] / r.asof(r.index[-1] - pd.Timedelta(days=365)) - 1)))
    ew = index_series("SPXEW.INDX")
    ew = ew[ew.index <= end]
    ratio = (g / ew).dropna()
    conc = pd.DataFrame([dict(
        opis="S&P 500 / S&P 500 równoważony", data=ratio.index[-1], poziom=float(ratio.iloc[-1]),
        percentyl_historii=float((ratio <= ratio.iloc[-1]).mean() * 100), data_maks=ratio.idxmax(),
        od_maks=float(ratio.iloc[-1] / ratio.max() - 1), zmiana_12m=float(ratio.iloc[-1] / ratio.asof(ratio.index[-1] - pd.Timedelta(days=365)) - 1),
        zmiana_5l=float(ratio.iloc[-1] / ratio.asof(ratio.index[-1] - pd.DateOffset(years=5)) - 1))])
    return {"indeksy": tbl, "sila_relatywna": pd.DataFrame(rs), "koncentracja": conc}


def sector_pe_summary(spe: pd.DataFrame, episodes: pd.DataFrame, as_of: str) -> pd.DataFrame:
    """Dla kazdego sektora: P/E dzis, mediany 5 i 10 lat, percentyl, P/E na szczytach i w dolkach bess (od 2011), ocena."""
    pv = spe.pivot(index="date", columns="sector", values="pe").sort_index()
    cov = spe.pivot(index="date", columns="sector", values="pokrycie").sort_index()
    end = pd.Timestamp(as_of)
    pv, cov = pv[pv.index <= end], cov[cov.index <= end]
    eps = episodes[(episodes["peak_date"] >= "2011-01-01")]
    rows = []
    for sec in pv.columns:
        s = pv[sec].dropna()
        if s.empty:
            continue
        now = float(s.iloc[-1])
        h10, h5 = s[s.index > s.index[-1] - pd.DateOffset(years=10)], s[s.index > s.index[-1] - pd.DateOffset(years=5)]
        pk = [float(s.asof(r.peak_date)) for r in eps.itertuples() if s.index[0] <= r.peak_date]
        tr = [float(s.asof(r.trough_date)) for r in eps.itertuples() if s.index[0] <= r.peak_date]
        comp = [t / p - 1 for p, t in zip(pk, tr) if p > 0 and np.isfinite(p) and np.isfinite(t)]
        perc = float((h10 <= now).mean() * 100)
        vs = now / float(h10.median()) - 1
        c = float(cov[sec].dropna().iloc[-1]) if sec in cov and cov[sec].notna().any() else np.nan
        ocena = "drogi" if perc >= 80 and vs >= 0.10 else ("tani" if perc <= 25 and vs <= -0.10 else "neutralny")
        if c < 0.35:
            ocena += " (niskie pokrycie)"
        rows.append(dict(sector=sec, pe_teraz=now, med_5l=float(h5.median()), med_10l=float(h10.median()), perc_10l=perc,
                         vs_med_10l=vs, pe_szczyt=float(np.nanmean(pk)) if pk else np.nan, pe_dolek=float(np.nanmean(tr)) if tr else np.nan,
                         kompresja=float(np.mean(comp)) if comp else np.nan, pokrycie=c, ocena=ocena))
    return pd.DataFrame(rows).sort_values("perc_10l", ascending=False).reset_index(drop=True)


def sensitivity_stage(ins, cand, m, trend, pe, beta4, beta7, ids4, ids7, min_b: int = 3) -> dict:
    """Czy ranking B (obecny uklad) przetrwa zmiane zbioru blizniakow: 4 najblizsze vs wszystkie kwalifikujace sie."""
    from .scoring import aggregate, rank_b
    st = cand[cand["kind"] == "stock"]
    ms = m[m["instrument_id"].isin(set(st["instrument_id"]))]
    r4 = rank_b(aggregate(ms, ids4), beta4, trend, st, pe, min_valid=min_b, top=30)["ref_ticker"].tolist()
    r7 = rank_b(aggregate(ms, ids7), beta7, trend, st, pe, min_valid=min_b, top=30)["ref_ticker"].tolist()
    s15, s30 = sens_summary(r4, r7, 15), sens_summary(r4, r7, 30)
    return {"overlap15": s15["overlap"], "overlap30": s30["overlap"], "ids7": ids7, "both": s15["both"],
            "only4": s15["only_a"], "only7": s15["only_b"]}


PE_REASON_LABEL = {
    "ujemny EPS": "ujemny zysk (EPS)", "P/E powyzej p80": "P/E powyżej własnego 80. percentyla", "ok": "przeszło bez uwag",
    "brak historii P/E": "przeszło z uwagą: brak historii P/E", "brak danych EPS": "przeszło z uwagą: brak danych EPS",
}


def pe_reason_tables(agg_a: pd.DataFrame, pe: pd.DataFrame, min_valid: int = 4, min_win: float = 0.7) -> dict:
    """Powody odrzucenia i przejscia filtra P/E dla spolek, ktore przeszly etap wygranych (spojne z lejkiem)."""
    win = agg_a[(agg_a["n_valid"] >= min_valid) & (agg_a["win_rate"] >= min_win)]
    sub = pe.reindex(win["instrument_id"])
    passed = sub["pe_pass"].fillna(True).astype(bool)
    reason = sub["pe_reason"].map(PE_REASON_LABEL).fillna("przeszło z uwagą: brak wyceny w bazie")

    def table(mask):
        return [dict(reason=r, n=int(n)) for r, n in reason[mask].value_counts().items()]
    return dict(rejected=table(~passed), passed=table(passed))


def funnel_steps(ins: pd.DataFrame, cand: pd.DataFrame, agg_a: pd.DataFrame, pe: pd.DataFrame, top: int) -> list[dict]:
    """Liczności kolejnych etapów selekcji spółek w rankingu A (do lejka na stronie)."""
    ok4 = agg_a[agg_a["n_valid"] >= 4]
    win = ok4[ok4["win_rate"] >= 0.7]
    passed = pe.reindex(win["instrument_id"])["pe_pass"].fillna(True).astype(bool)
    return [
        dict(key="akcje_w_bazie", label="Spółki w bazie", n=int((ins["kind"] == "stock").sum()),
             note="wszystkie akcje w bazie, także zdjęte z giełdy"),
        dict(key="kandydaci", label="Kupowalni kandydaci", n=int((cand["kind"] == "stock").sum()),
             note="giełdy XTB, obrót co najmniej 1 mln USD, bez funduszy zamkniętych"),
        dict(key="min4", label="Co najmniej 4 ważne okresy", n=int(len(ok4)), note="okresy spadkowe od 1962"),
        dict(key="win70", label="Pokonują S&P 500 w co najmniej 70% okresów", n=int(len(win)), note="odsetek wygranych"),
        dict(key="pe_ok", label="Po filtrze P/E", n=int(passed.sum()),
             note="odrzucone: ujemny zysk i P/E powyżej własnego 80. percentyla"),
        dict(key="top", label="Lista Top", n=int(top), note="wynik złożony: alfa, downside beta, max DD, odsetek wygranych"),
    ]
