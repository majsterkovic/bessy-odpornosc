"""Eksport wynikow badania do JSON dla strony (web/public/data). Uruchomienie: python -m bessy.export_web"""
import argparse
import datetime as dt
import json
from pathlib import Path

import pandas as pd

from .report import why_text
from .serialize import to_jsonable

ROOT = Path(__file__).resolve().parent.parent
VERSION = 1
LIST_FIELDS = {"ref_ticker": "ticker", "name": "name", "sector": "sector", "exchange_code": "exchange", "n_valid": "n_valid",
               "n_bessy": "n_bessy", "med_alpha": "med_alpha", "downside_beta": "downside_beta", "med_max_dd": "med_max_dd",
               "win_rate": "win_rate", "pe": "pe", "pe_pct": "pe_pct", "uwagi": "note", "alpha_od_szczytu_sox": "alpha_sox",
               "alpha_63d": "alpha_63d", "classe": "klass", "corr_spx": "corr_spx", "odpowiedniki_ucits": "ucits",
               "instrument_id": "instrument_id"}
ROW_KEYS = ["rank", "instrument_id", "ticker", "name", "sector", "exchange", "currency", "n_valid", "n_bessy", "med_alpha", "downside_beta",
            "med_max_dd", "win_rate", "pe", "pe_pct", "note", "alpha_sox", "alpha_63d", "klass", "corr_spx", "ucits"]


def _clean(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) or v == "" else v


def _list_rows(df: pd.DataFrame, metrics: pd.DataFrame, episode_ids: list[str]) -> list[dict]:
    if df is None or len(df) == 0:
        return []
    m = metrics[metrics["valid"] & metrics["episode_id"].isin(episode_ids)]
    per = {i: g.sort_values("episode_id")[["episode_id", "alpha"]].to_dict("records") for i, g in m.groupby("instrument_id")}
    out = []
    for rank, (_, r) in enumerate(df.iterrows(), 1):
        row = {k: None for k in ROW_KEYS}
        for src, dst in LIST_FIELDS.items():
            if src in r.index:
                row[dst] = _clean(r[src])
        cur = r.get("waluta") if "waluta" in r.index else None
        row["currency"] = _clean(cur) if _clean(cur) is not None else _clean(r.get("currency"))
        row["rank"] = rank
        row["why"] = why_text(r)
        row["per_episode"] = per.get(r["instrument_id"], [])
        out.append(row)
    return to_jsonable(out)


def build_payloads(wyniki_dir: Path, metrics_path: Path) -> dict:
    k = json.loads((Path(wyniki_dir) / "kontekst.json").read_text(encoding="utf-8"))
    c = k["ctx"]
    ids_a, ids_b = k["kolejnosc_a"], k["kolejnosc_b"]
    ep = pd.read_csv(Path(wyniki_dir) / "epizody.csv")
    ep["in_ranking_a"] = ep["episode_id"].isin(ids_a)
    ep["twin"] = ep["episode_id"].isin(ids_b)
    keep = ["episode_id", "peak_date", "trough_date", "depth", "days_to_trough", "days_to_recovery", "kind", "n_factors",
            "oil_shock", "tech_hot", "midterm", "in_ranking_a", "twin"]
    metrics = pd.read_csv(metrics_path, usecols=["instrument_id", "episode_id", "alpha", "valid"])
    metrics["valid"] = metrics["valid"].astype(bool)
    lists = {"stocks_a": _list_rows(pd.DataFrame(c["top_a_spolki"]), metrics, ids_a),
             "stocks_b": _list_rows(pd.DataFrame(c["top_b_spolki"]), metrics, ids_b),
             "etf_a": _list_rows(pd.DataFrame(c["top_a_etf"]), metrics, ids_a),
             "etf_b": _list_rows(pd.DataFrame(c["top_b_etf"]), metrics, ids_b)}
    return to_jsonable({
        "meta": dict(as_of=c["as_of"], generated_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M"), version=VERSION, notes=c["zalozenia"]),
        "market": dict(summary=c["podsumowanie"], state_text=c["stan_tekst"], indices=c["stan"], factors=c["czynniki_teraz"]),
        "episodes": dict(rows=ep[keep], brief_text=c["brief_tekst"]),
        "twins": dict(text=c["blizniaki_tekst"], seasonality_monthly=c["sezonowosc_mies"], after_election=c["po_wyborach"],
                      after_election_text=c["po_wyborach_tekst"]),
        "sectors": dict(behavior_a=c["sektory_a"], behavior_b=c["sektory_b"], pe=c["sektory_pe"], pe_text=c["sektory_pe_tekst"]),
        "funnel": dict(steps=k["lejek"], pe_rejected=k["pe_tabele"]["rejected"], pe_passed=k["pe_tabele"]["passed"]),
        "validation": dict(text=c["walidacja"], oos=k["oos"], sensitivity=k["sens"]),
        "lists": lists,
    })


def _rel_path(s: pd.Series, start, end=None, max_points: int | None = None) -> list:
    start = pd.Timestamp(start)
    seg = s[s.index >= start]
    if end is not None:
        seg = seg[seg.index <= pd.Timestamp(end)]
    if max_points:
        seg = seg.iloc[:max_points]
    return [[int((d - start).days), round(float(v / seg.iloc[0] * 100), 2)] for d, v in seg.items()]


def series_payload(twin_ids: list, twin_peaks: list, last_ath, as_of) -> dict:
    """Szeregi do wykresow (baza tylko do odczytu): S&P 500 i SOX tygodniowo, sciezki bliznikow od szczytu, sciezka 'dzis'."""
    from .db import index_series
    gspc, sox = index_series("GSPC.INDX"), index_series("SOX.INDX")
    asof = pd.Timestamp(as_of)
    gspc, sox = gspc[gspc.index <= asof], sox[sox.index <= asof]

    def weekly(s):
        # etykieta tygodnia = ostatni realny dzien notowan w tygodniu (nie piatek po koncu danych)
        last = s.groupby(s.index.to_period("W-FRI")).tail(1)
        return [[d.strftime("%Y-%m-%d"), round(float(v), 2)] for d, v in last.items()]
    return to_jsonable({
        "sp500": weekly(gspc), "sox": weekly(sox),
        "twins": [dict(episode_id=i, path=_rel_path(gspc, p, max_points=600)) for i, p in zip(twin_ids, twin_peaks)],
        "today": dict(peak_date=pd.Timestamp(last_ath).strftime("%Y-%m-%d"), path=_rel_path(gspc, last_ath, asof)),
    })


def main(out_dir: Path | None = None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "web" / "public" / "data"))
    a = ap.parse_args()
    out = Path(out_dir or a.out)
    out.mkdir(parents=True, exist_ok=True)
    wyniki = ROOT / "wyniki"
    p = build_payloads(wyniki, wyniki / "metryki.csv.gz")
    k = json.loads((wyniki / "kontekst.json").read_text(encoding="utf-8"))
    eps = {r["episode_id"]: r for r in p["episodes"]["rows"]}
    tw = k["kolejnosc_b"]
    sp = next(r for r in p["market"]["indices"] if r["ticker"] == "GSPC.INDX")
    p["series"] = series_payload(tw, [eps[i]["peak_date"] for i in tw], sp["data_ath"], p["meta"]["as_of"])
    for name, obj in p.items():
        (out / f"{name}.json").write_text(json.dumps(obj, allow_nan=False, ensure_ascii=False), encoding="utf-8")
    print(f"zapisano {len(p)} plikow w {out}")


if __name__ == "__main__":
    main()
