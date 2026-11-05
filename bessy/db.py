"""Dostep do bazy marketdata, tylko do odczytu."""
import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]


def connect() -> psycopg.Connection:
    load_dotenv(ROOT / ".env")
    return psycopg.connect(os.environ["PG_DSN"], options="-c default_transaction_read_only=on")


def query_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    with connect() as c, c.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def index_series(ticker: str, field: str = "close") -> pd.Series:
    if field not in {"close", "adj_close", "volume"}:
        raise ValueError(field)
    df = query_df(
        f"select p.date, p.{field} v from daily_price p join instrument i using(instrument_id) "
        "where i.ref_ticker = %(t)s and p.{0} is not null order by p.date".format(field),
        {"t": ticker},
    )
    s = pd.Series(df["v"].astype(float).values, index=pd.to_datetime(df["date"]), name=ticker)
    return s
