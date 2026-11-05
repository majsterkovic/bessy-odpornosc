import pandas as pd
import psycopg
import pytest

from bessy.db import connect, index_series


@pytest.mark.db
def test_write_is_refused():
    with connect() as c, pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        c.execute("CREATE TABLE _probe(x int)")


@pytest.mark.db
def test_gspc_history():
    s = index_series("GSPC.INDX")
    assert str(s.index.min().date()) == "1927-12-30"
    assert s.index.max() >= pd.Timestamp("2026-10-23")
